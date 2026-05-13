import os
import pickle
import json
import traceback
import warnings
from collections import defaultdict

import pandas as pd
import numpy as np

warnings.filterwarnings(action="ignore")


from pages.helper import db_queries


def normalize_face_mesh(face_mesh):
    """
    Make landmark vectors comparable across different crops and image sizes.

    MediaPipe gives x/y positions relative to the full image. Without this step,
    the same face can look far away numerically just because the photo is zoomed,
    shifted, or cropped differently.
    """
    points = np.asarray(face_mesh, dtype=float).reshape(-1, 3)
    center = points.mean(axis=0)
    centered = points - center

    xy_scale = np.sqrt(np.mean(np.sum(centered[:, :2] ** 2, axis=1)))
    z_scale = np.std(centered[:, 2]) or xy_scale
    scale = max(float(xy_scale), float(z_scale), 1e-6)

    return (centered / scale).flatten()


def _feature_matrix(df: pd.DataFrame, start_col: int) -> np.ndarray:
    rows = df.iloc[:, start_col:].values.astype(float)
    return np.vstack([normalize_face_mesh(row) for row in rows])


def get_public_cases_data(status="NF"):
    try:
        result = db_queries.fetch_public_cases(train_data=True, status=status)
        d1 = pd.DataFrame(result, columns=["label", "face_mesh"])
        d1["face_mesh"] = d1["face_mesh"].apply(lambda x: json.loads(x))
        d2 = pd.DataFrame(d1.pop("face_mesh").values.tolist(), index=d1.index).rename(
            columns=lambda x: "fm_{}".format(x + 1)
        )
        df = d1.join(d2)
        # Ensure all columns except label are float
        for col in df.columns:
            if col != "label":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    except Exception as e:
        traceback.print_exc()
        return None


def get_registered_cases_data(status="NF"):
    try:
        from pages.helper.db_queries import engine, RegisteredCases
        import pandas as pd
        import json
        from sqlmodel import Session, select

        with Session(engine) as session:
            result = session.exec(
                select(
                    RegisteredCases.id,
                    RegisteredCases.face_mesh,
                    RegisteredCases.status,
                )
            ).all()
            d1 = pd.DataFrame(result, columns=["label", "face_mesh", "status"])
            if status:
                d1 = d1[d1["status"] == status]
            d1["face_mesh"] = d1["face_mesh"].apply(lambda x: json.loads(x))
            d2 = pd.DataFrame(
                d1.pop("face_mesh").values.tolist(), index=d1.index
            ).rename(columns=lambda x: "fm_{}".format(x + 1))
            df = d1.join(d2)
            # Ensure all columns except label and status are float
            for col in df.columns:
                if col not in ["label", "status"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
    except Exception as e:
        traceback.print_exc()
        return None


from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder


def match(distance_threshold=0.08, margin_threshold=0.01):
    matched_images = defaultdict(list)
    public_cases_df = get_public_cases_data()
    registered_cases_df = get_registered_cases_data()

    if public_cases_df is None or registered_cases_df is None:
        return {"status": False, "message": "Couldn't connect to database"}
    if len(public_cases_df) == 0 or len(registered_cases_df) == 0:
        return {"status": False, "message": "No public or registered cases found"}

    # Store original labels before encoding
    original_reg_labels = registered_cases_df.iloc[:, 0].tolist()
    original_pub_labels = public_cases_df.iloc[:, 0].tolist()

    # Prepare normalized landmark features - use index positions as labels.
    reg_features = _feature_matrix(registered_cases_df, start_col=2)

    # For each public submission, find the closest registered case
    for enum_idx, (df_idx, row) in enumerate(public_cases_df.iterrows()):
        pub_label = original_pub_labels[enum_idx]  # Use enumeration index, not df index
        face_encoding = normalize_face_mesh(np.array(row[1:]).astype(float))

        try:
            similarities = reg_features @ face_encoding / (
                np.linalg.norm(reg_features, axis=1) * np.linalg.norm(face_encoding)
            )
            distances = 1.0 - similarities
            ranked_indices = np.argsort(distances)

            predicted_idx = int(ranked_indices[0])
            closest_distance = float(distances[predicted_idx])
            second_distance = (
                float(distances[int(ranked_indices[1])])
                if len(ranked_indices) > 1
                else 1.0
            )
            margin = second_distance - closest_distance

            # Require both a strong match and a clear gap from the next candidate.
            if closest_distance <= distance_threshold and margin >= margin_threshold:
                reg_label = original_reg_labels[predicted_idx]
                matched_images[reg_label].append((pub_label, float(closest_distance)))
        except Exception as e:
            continue

    return {"status": True, "result": matched_images}


if __name__ == "__main__":
    result = match()
    print(result)
