import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    st.markdown(
        """
        <div style="text-align:center; padding-top:20px;">
            <h1>🏋️ AI Real-Time Gym Coach</h1>
            <h3 style="color:#4CAF50;">
                Your Intelligent AI Fitness Partner
            </h3>
            <p style="font-size:18px; color:gray;">
                Train smarter with real-time pose detection,
                AI voice coaching, form correction and workout analytics.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("### 👤 Start Your Fitness Journey")

    with st.form("login_form", clear_on_submit=False):

        username = st.text_input(
            "Username",
            placeholder="Choose a unique username"
        )

        submit_button = st.form_submit_button(
            "🚀 Start Training",
            use_container_width=True
        )

    if submit_button:

        if not username.strip():
            st.error("⚠ Please enter a username.")
            return False

        user = get_or_create_user(username.strip())

        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]

        st.success(f"Welcome, {user['username']}! Let's begin your workout.")

        st.rerun()

    st.markdown("---")

    st.markdown(
        """
        #### 🚀 Features

        ✅ Real-Time Pose Detection

        ✅ Automatic Rep Counting

        ✅ AI Voice Coaching

        ✅ Form Correction

        ✅ Workout History & Progress Tracking
        """
    )

    return False