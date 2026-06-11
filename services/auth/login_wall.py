import streamlit as st

from services.persistence.exercise_repository import get_or_create_user
def render_login_wall():
    # session state is a dictionary in which we store data in key value pair
    if st.session_state.get("user_id") is not None: #if user is already logged in we will return ture else false
        return True
    st.title("🏋️‍♂️ AI Realtime Gym Coach")
    st.markdown(" :muscle: Welcome! Please enter username to start.")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Name (unique)",placeholder="unique name e.g. jiya")

        submit_button = st.form_submit_button("Start session", width="stretch") 

    if submit_button:
        if not username:
            st.error("Please enter a username.")
            return False
        
        user=get_or_create_user(username)

        st.session_state["username"] = user["username"]
        st.session_state["user_id"] = user["id"]
        st.rerun()
        
    return False