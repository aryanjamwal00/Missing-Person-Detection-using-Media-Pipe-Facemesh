import os
import uuid
import json
import tempfile

import streamlit as st
from PIL import Image

from pages.helper import db_queries
from pages.helper.data_models import PublicSubmissions
from pages.helper.utils import (
    image_obj_to_numpy,
    extract_face_mesh_landmarks,
    extract_unique_faces_from_video,
)
from pages.helper.validators import (
    Validators,
    validate_public_submission_form,
    ValidationError
)
from pages.helper.auth import render_auth_flow

st.set_page_config("Public Submission", initial_sidebar_state="collapsed")

st.session_state["login_status"] = False
st.session_state.pop("user", None)
st.session_state.pop("role", None)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Report a Sighting")

# Security verification - but don't block the entire page
is_authenticated = render_auth_flow(required=False)

upload_mode = st.radio(
    "Upload type",
    options=["Image", "Video"],
    horizontal=True,
)

image_col, form_col = st.columns(2)
save_flag = 0
extracted_faces = []  # list of (landmarks, frame_rgb) for video mode
face_mesh = None  # single face for image mode
face_detected = False
unique_id = None
uploaded_file_path = None

# ── Image upload ──────────────────────────────────────────────────────────────
if upload_mode == "Image":
    with image_col:
        image_obj = st.file_uploader(
            "Upload photo", type=["jpg", "jpeg", "png"], key="user_submission_img"
        )
        if image_obj:
            with st.spinner("Processing..."):
                try:
                    uploaded_file_path, unique_id = Validators.validate_file_upload(
                        image_obj,
                        Validators.ALLOWED_IMAGE_TYPES,
                        Validators.MAX_IMAGE_SIZE,
                        "Photo"
                    )
                    
                    with open(uploaded_file_path, "wb") as f:
                        f.write(image_obj.read())

                    image_obj.seek(0)
                    st.image(image_obj, width=200)
                    image_obj.seek(0)
                    image_numpy = image_obj_to_numpy(image_obj)
                    face_mesh = extract_face_mesh_landmarks(image_numpy)

                    if face_mesh is None:
                        if uploaded_file_path and os.path.exists(uploaded_file_path):
                            os.remove(uploaded_file_path)
                    else:
                        face_detected = True
                        st.success("✅ Face detected.")
                except ValidationError as e:
                    st.error(f"❌ {str(e)}")
                    face_detected = False
                    unique_id = None
                    uploaded_file_path = None

    if image_obj and face_detected:
        with form_col.form(key="image_submission_form"):
            sub_name = st.text_input("Your Name *")
            mobile_number = st.text_input("Your Mobile Number * (10 digits)")
            email = st.text_input("Your Email")
            address = st.text_input("Location where person was seen *")
            birth_marks = st.text_input("Birth Marks / Identifying Features")

            submit_bt = st.form_submit_button("Submit")

            if submit_bt:
                # Check authentication before submission
                if not is_authenticated:
                    st.error("❌ Please complete the security verification first")
                    st.stop()
                
                form_data = {
                    'sub_name': sub_name,
                    'mobile_number': mobile_number,
                    'email': email,
                    'address': address,
                    'birth_marks': birth_marks,
                }
                
                is_valid, errors, sanitized_data = validate_public_submission_form(form_data)
                
                if not is_valid:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    details = PublicSubmissions(
                        submitted_by=sanitized_data['sub_name'],
                        location=sanitized_data['address'],
                        email=sanitized_data['email'],
                        face_mesh=json.dumps(face_mesh),
                        id=unique_id,
                        mobile=sanitized_data['mobile_number'],
                        birth_marks=sanitized_data['birth_marks'],
                        status="NF",
                    )
                    db_queries.new_public_case(details)
                    save_flag = 1

        if save_flag == 1:
            st.success("✅ Submission received. Thank you!")

# ── Video upload ──────────────────────────────────────────────────────────────
else:
    with image_col:
        video_obj = st.file_uploader(
            "Upload video", type=["mp4", "mov", "avi"], key="user_submission_video"
        )
        if video_obj:
            with st.spinner("Extracting faces from video..."):
                try:
                    # Validate video file
                    uploaded_file_path, unique_id = Validators.validate_file_upload(
                        video_obj,
                        Validators.ALLOWED_VIDEO_TYPES,
                        Validators.MAX_VIDEO_SIZE,
                        "Video"
                    )
                    
                    # Save to temp file so OpenCV can read it
                    suffix = "." + video_obj.name.rsplit(".", 1)[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(video_obj.read())
                        tmp_path = tmp.name

                    extracted_faces = extract_unique_faces_from_video(tmp_path)
                    os.unlink(tmp_path)
                except ValidationError as e:
                    st.error(f"❌ {str(e)}")
                    extracted_faces = []

                if not extracted_faces:
                    st.error(
                        "❌ No faces detected in the video.\n\n"
                        "**Tips:** ensure the video shows a clear front-facing view "
                        "of the person's face in good lighting."
                    )
                else:
                    st.success(f"✅ Found {len(extracted_faces)} unique face(s).")
                    st.caption("Detected faces:")
                    thumb_cols = st.columns(min(len(extracted_faces), 4))
                    for idx, (_, frame_rgb) in enumerate(extracted_faces):
                        thumb_cols[idx % 4].image(frame_rgb, width=100)

    if extracted_faces:
        with form_col.form(key="video_submission_form"):
            sub_name = st.text_input("Your Name *")
            mobile_number = st.text_input("Your Mobile Number * (10 digits)")
            email = st.text_input("Your Email")
            address = st.text_input("Location where person was seen *")
            birth_marks = st.text_input("Birth Marks / Identifying Features")

            submit_bt = st.form_submit_button(f"Submit {len(extracted_faces)} face(s)")

            if submit_bt:
                # Check authentication before submission
                if not is_authenticated:
                    st.error("❌ Please complete the security verification first")
                    st.stop()
                
                form_data = {
                    'sub_name': sub_name,
                    'mobile_number': mobile_number,
                    'email': email,
                    'address': address,
                    'birth_marks': birth_marks,
                }
                
                is_valid, errors, sanitized_data = validate_public_submission_form(form_data)
                
                if not is_valid:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    count = 0
                    for landmarks, frame_rgb in extracted_faces:
                        sub_id = str(uuid.uuid4())
                        Image.fromarray(frame_rgb).save(f"./resources/{sub_id}.jpg")
                        details = PublicSubmissions(
                            submitted_by=sanitized_data['sub_name'],
                            location=sanitized_data['address'],
                            email=sanitized_data['email'],
                            face_mesh=json.dumps(landmarks),
                            id=sub_id,
                            mobile=sanitized_data['mobile_number'],
                            birth_marks=sanitized_data['birth_marks'],
                            status="NF",
                        )
                        db_queries.new_public_case(details)
                        count += 1
                    st.success(f"✅ {count} submission(s) received. Thank you!")
