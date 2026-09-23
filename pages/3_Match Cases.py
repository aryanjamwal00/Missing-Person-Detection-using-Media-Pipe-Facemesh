import streamlit as st

from pages.helper import db_queries, emailer, match_algo, train_model


def confidence_from_distance(distance: float) -> float:
    """Convert cosine distance to a 0-100 confidence percentage."""
    return max(0.0, min(100.0, (1.0 - distance) * 100))


def case_viewer(
    registered_case_id: str,
    public_case_id: str,
    confidence: float = None,
    email_result=None,
):
    try:
        case_details = db_queries.get_registered_case_detail(registered_case_id)[0]
        public_details = db_queries.get_public_case_detail(public_case_id)
        public_details = public_details[0] if public_details else None

        data_col, reg_image_col, public_col = st.columns([2, 1, 2])

        labels = ["Name", "Mobile", "Age", "Last Seen", "Birth Marks"]
        display_values = [
            case_details[0],
            case_details[1],
            case_details[3],
            case_details[4],
            case_details[5],
        ]
        for text, value in zip(labels, display_values):
            data_col.write(f"**{text}:** {value}")

        if confidence is not None:
            data_col.write("")
            data_col.success(f"Match Found - {confidence:.0f}% accuracy")
            data_col.progress(confidence / 100, text=f"{confidence:.0f}% accuracy")
        else:
            data_col.success("Match Found")

        try:
            reg_image_col.image(
                "./resources/" + registered_case_id + ".jpg",
                width=100,
            )
            reg_image_col.caption("Registered case")
        except Exception as img_err:
            reg_image_col.warning(f"Could not load image: {str(img_err)}")

        try:
            public_col.image(
                "./resources/" + public_case_id + ".jpg",
                width=100,
            )
            public_col.caption("Public submission")
        except Exception:
            pass

        if public_details:
            public_col.write(f"**Location:** {public_details[0]}")
            public_col.write(f"**Submitted By:** {public_details[1]}")
            public_col.write(f"**Mobile:** {public_details[2]}")
            public_col.write(f"**Birth Marks:** {public_details[3]}")

        if email_result:
            st.info(f"Notification sent to {email_result.recipient}")
        elif email_result is not None:
            st.warning(email_result.message)

    except Exception as e:
        import traceback

        traceback.print_exc()
        st.error(f"Something went wrong: {str(e)}. Please check logs.")


if "login_status" not in st.session_state:
    st.write("You don't have access to this page")

elif st.session_state["login_status"]:
    user = st.session_state.user
    is_admin = st.session_state.get("role", "").lower() == "admin"

    st.title("Check for Match")

    if not is_admin:
        st.info("Only Admins can trigger the matching process.")
    else:
        col1, col2 = st.columns(2)
        refresh_bt = col1.button("Refresh")
        st.write("---")

        if refresh_bt:
            with st.spinner("Fetching data and checking for confident matches..."):
                result = train_model.train(user)
                matched_ids = match_algo.match()

                if matched_ids["status"] and matched_ids["result"]:
                    for matched_id, submitted_cases in matched_ids["result"].items():
                        for submitted_case in submitted_cases:
                            if isinstance(submitted_case, tuple):
                                submitted_case_id, distance = submitted_case
                                conf = confidence_from_distance(distance)
                            else:
                                submitted_case_id = submitted_case
                                conf = None

                            case_details = db_queries.get_registered_case_detail(
                                matched_id
                            )[0]
                            db_queries.update_found_status(
                                matched_id, submitted_case_id
                            )
                            email_result = emailer.send_match_notification(
                                matched_id, case_details
                            )
                            case_viewer(
                                matched_id,
                                submitted_case_id,
                                conf,
                                email_result=email_result,
                            )
                            st.write("---")
                else:
                    st.info("No confident matches found.")

else:
    st.write("You don't have access to this page")
