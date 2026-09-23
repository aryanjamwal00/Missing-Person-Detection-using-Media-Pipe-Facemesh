import os
import uuid
import json

import streamlit as st

from pages.helper.data_models import RegisteredCases
from pages.helper import db_queries
from pages.helper.utils import image_obj_to_numpy, detect_all_faces, draw_face_boxes
from pages.helper.validators import (
    Validators,
    validate_case_registration_form,
    ValidationError
)

st.set_page_config(page_title="Register New Case")


if "login_status" not in st.session_state:
    st.write("You don't have access to this page")

elif st.session_state["login_status"]:
    user = st.session_state.user

    st.title("Register New Case")

    image_col, form_col = st.columns(2)
    save_flag = 0

    with image_col:
        image_obj = st.file_uploader(
            "Upload Photo", type=["jpg", "jpeg", "png"], key="new_case"
        )

        if image_obj:
            # Cache detection results in session state keyed by file identity
            file_key = f"{image_obj.name}_{image_obj.size}"

            if st.session_state.get("nc_file_key") != file_key:
                # New image uploaded — run detection and cache results
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

                    with st.spinner("Detecting faces..."):
                        image_numpy = image_obj_to_numpy(image_obj)
                        faces = detect_all_faces(image_numpy, max_faces=5)
                except ValidationError as e:
                    st.error(f"❌ {str(e)}")
                    faces = []
                    unique_id = None
                    uploaded_file_path = None

                if not faces:
                    # Clean up orphaned image
                    if uploaded_file_path and os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                    st.session_state["nc_file_key"] = file_key
                    st.session_state["nc_faces"] = []
                    st.session_state["nc_image_numpy"] = None
                    st.session_state["nc_unique_id"] = None
                    st.session_state["nc_uploaded_path"] = None
                else:
                    st.session_state["nc_file_key"] = file_key
                    st.session_state["nc_faces"] = faces
                    st.session_state["nc_image_numpy"] = image_numpy
                    st.session_state["nc_unique_id"] = unique_id
                    st.session_state["nc_uploaded_path"] = uploaded_file_path

            # Read cached state
            faces = st.session_state.get("nc_faces", [])
            image_numpy = st.session_state.get("nc_image_numpy")
            unique_id = st.session_state.get("nc_unique_id")

            if not faces:
                st.error(
                    "❌ No face detected in this image.\n\n"
                    "**Tips:** use a well-lit, front-facing photo with one clear face visible."
                )
                selected_face_idx = None
            elif len(faces) == 1:
                # Single face — highlight and auto-select
                annotated = draw_face_boxes(image_numpy, faces, selected_idx=0)
                st.image(annotated, width="stretch")
                st.success("✅ 1 face detected.")
                selected_face_idx = 0
            else:
                # Multiple faces — let user pick
                st.warning(
                    f"⚠️ {len(faces)} faces detected. Select the person to register:"
                )
                options = [f"Face {i + 1}" for i in range(len(faces))]
                choice = st.radio(
                    "Select face", options, horizontal=True, key="nc_face_choice"
                )
                selected_face_idx = options.index(choice)
                annotated = draw_face_boxes(
                    image_numpy, faces, selected_idx=selected_face_idx
                )
                st.image(annotated, width="stretch")
                st.info(f"Using **Face {selected_face_idx + 1}** for registration.")
        else:
            # File uploader cleared — reset cached state
            for k in [
                "nc_file_key",
                "nc_faces",
                "nc_image_numpy",
                "nc_unique_id",
                "nc_uploaded_path",
            ]:
                st.session_state.pop(k, None)
            selected_face_idx = None
            unique_id = None
            faces = []

    # ── Registration form ─────────────────────────────────────────────────────
    face_ready = image_obj and faces and selected_face_idx is not None

    if face_ready:
        with form_col.form(key="new_case_form"):
            name = st.text_input("Name *")
            father_name = st.text_input("Father's Name")
            age = st.number_input("Age", min_value=1, max_value=120, value=10, step=1)
            mobile_number = st.text_input("Mobile Number (10 digits)")
            adhaar_card = st.text_input("Aadhaar Card (12 digits)")
            address = st.text_input("Address")
            city = st.text_input("City *")
            birthmarks = st.text_input("Birth Marks")
            last_seen = st.text_input("Last Seen *")
            description = st.text_area("Description (optional)")

            st.markdown("**Complainant Details**")
            complainant_name = st.text_input("Complainant Name *")
            complainant_phone = st.text_input("Complainant Phone * (10 digits)")
            complainant_email = st.text_input("Complainant Email")

            submit_bt = st.form_submit_button("Save Case")

            if submit_bt:
                form_data = {
                    'name': name,
                    'father_name': father_name,
                    'age': age,
                    'mobile_number': mobile_number,
                    'adhaar_card': adhaar_card,
                    'address': address,
                    'city': city,
                    'birthmarks': birthmarks,
                    'last_seen': last_seen,
                    'description': description,
                    'complainant_name': complainant_name,
                    'complainant_phone': complainant_phone,
                    'complainant_email': complainant_email,
                }
                
                is_valid, errors, sanitized_data = validate_case_registration_form(form_data)
                
                if not is_valid:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    selected_landmarks = faces[selected_face_idx]["landmarks"]
                    new_case_details = RegisteredCases(
                        id=unique_id,
                        submitted_by=user,
                        name=sanitized_data['name'],
                        father_name=sanitized_data['father_name'],
                        age=sanitized_data['age'],
                        complainant_mobile=sanitized_data['complainant_phone'],
                        complainant_name=sanitized_data['complainant_name'],
                        complainant_email=sanitized_data['complainant_email'],
                        face_mesh=json.dumps(selected_landmarks),
                        adhaar_card=sanitized_data['adhaar_card'],
                        birth_marks=sanitized_data['birthmarks'],
                        address=sanitized_data['address'],
                        city=sanitized_data['city'],
                        last_seen=sanitized_data['last_seen'],
                        description=sanitized_data['description'],
                        status="NF",
                        matched_with="",
                    )
                    db_queries.register_new_case(new_case_details)
                    save_flag = 1

        if save_flag:
            st.success("✅ Case registered successfully.")

else:
    st.write("You don't have access to this page")
