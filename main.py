from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import time
import pandas as pd
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio


def main():
    st.set_page_config(
        page_icon=":muscle:",
        page_title="Your Intelligent AI Fitness Partner",
        initial_sidebar_state="expanded",
        layout="centered"
        )
    
    load_css(os.path.join(os.getcwd(), "static", "style.css"))
    inject_local_font(os.path.join(os.getcwd(), "static", "AdobeClean.otf"), "Adobe Clean")
  
    init_db()


    # if the user is not logged in, we will show the login wall and return early to prevent access to the rest of the app
    if not render_login_wall():
        return
    # If the user is logged in, we initialize session defaults.
    initial_session_defaults()
    if "voice_pipeline" not in st.session_state:
        try:
            api_key = os.getenv("GROQ_API_KEY")

            if not api_key:
                raise Exception("GROQ_API_KEY not found")
            
            groq_client = Groq(api_key=api_key)
            llm_coach = LLMCoach(groq_client)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
        except Exception as e:
            st.error(f"VOICE PIPELINE ERROR: {e}")
            print("VOICE PIPELINE ERROR:", e)
            st.session_state.voice_pipeline = None
    
    workout_started=st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("Personal Trainer")
        if st.session_state.username:
            st.caption(f"👋 Hello, {st.session_state.username}")
        st.divider()
        st.subheader("Workout Plan")

        if not workout_started:

            plan_exercise=st.selectbox("Exercise", options = EXERCISE_OPTIONS, key="plan_exercise") 

            plan_sets=st.number_input("Sets", min_value=0, max_value=50, step=1, key="plan_sets")
            plan_reps=st.number_input("Reps per Set", min_value=0, max_value=50, step=1, key="plan_reps")
            st.markdown("")


            start_session_button=st.button("Start Workout", width="stretch",key="start_session_button")


            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={}
                    )
                    
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.rerun()
        else:
            exercise=st.session_state.get("exercise_type")
            sets=st.session_state.get("target_sets")
            reps=st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** -- {sets} sets / {reps} reps")
            end_session_button=st.button("End Workout",width="stretch", key="end_session_button")
            if end_session_button:
                st.session_state.workout_started = False
                
                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.rerun()

        if workout_started:
            st.divider()
        # If the workout has started, we show the real-time workout tracking metrics
            exercise=st.session_state.get("exercise_type")
            total_reps=st.session_state.get("reps")
            current_set_reps=st.session_state.get("current_set_reps")
            reps_per_set=st.session_state.get("reps_per_set")
            sets_completed=st.session_state.get("sets_completed")
            target_sets=st.session_state.get("target_sets")

            st.subheader("Progress")

            st.metric("Total reps",f"{total_reps}") 
            st.metric("Current set reps",f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets completed",f"{sets_completed} / {target_sets}")
            st.divider()

            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                st.metric("Back Angle", f"{st.session_state.back_angle}°")
                st.metric("Depth Status", st.session_state.depth_status)

            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Body Alignment", st.session_state.body_alignment)
                st.metric("Hip Position", st.session_state.hip_status)

            elif exercise == "Biceps Curls (Dumbbell)":
                st.subheader("Curl Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Shoulder Stability", st.session_state.shoulder_status)
                st.metric("Swing Detection", st.session_state.swing_status)

            elif exercise == "Shoulder Press":
                st.subheader("Shoulder Press Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Arm Extension", st.session_state.extension_status)
                st.metric("Back Arch", st.session_state.back_arch_status)

            elif exercise == "Lunges":
                st.subheader("Lunge Metrics")
                st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                st.metric("Balance Status", st.session_state.balance_status)


    st.title("Your Intelligent AI Fitness Partner")
    st.markdown("Train Smarter with Real-Time AI Guidance, Real-time pose detection, intelligent form correction, AI voice coaching, and workout performance tracking! :muscle:")

    if st.session_state.get("audio_to_play"):
        autoplay_audio(st.session_state.audio_to_play)

    if st.session_state.get("coach_feedback"):
        st.markdown("")
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")
    if not workout_started:
        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
                margin-bottom: 32px;
            ">
                <h2 style="color:#ccc; margin-bottom:8px;">👈 Set your workout plan</h2>
                <p style="font-size:1.05rem;">
                    Choose your exercise, sets and reps in the sidebar,<br>
                    then click <strong>Start Workout</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        #WebRTC is generally peer to peer , allowing direct browser to browser communication, but in this case we are using it for local webcam access and streamlit's WebRTC component handles the video feed in an iframe which has its own styles that can interfere with our app's styles, so we need to inject our custom font and styles into that iframe to ensure a consistent look and feel across the entire app, including the webcam feed and AI feedback overlays.
        #WebRTC uses UDP for speed and is built for high speed real time media streaming, which is ideal for our use case of real-time pose detection and feedback during workouts, as it minimizes latency and allows for a smoother user experience.
        #Websockets are optimized for sending text or json data and are not suited for streaming video data, which can lead to higher latency and a less responsive experience when trying to provide real-time feedback based on webcam input.
    else:
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={
                "iceServers": [
                    {"urls": ["stun:stun.l.google.com:19302"]},
                    {"urls": ["stun:stun1.l.google.com:19302"]},
                    {"urls": ["stun:stun2.l.google.com:19302"]},
                    {"urls": ["stun:stun.cloudflare.com:3478"]},
           ]
          },
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True,
        )

        sync_metrics_update(context)

        if context.state.playing:
            time.sleep(0.25)
            st.rerun()

        inject_webrtc_styles()

    st.divider()

    st.markdown("#### Workout History")

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id, int):
        history_rows = get_users_exercises(user_id)

        arr = [
            {
                "Exercise": row['exercise_name'],
                "Reps": row['reps'],
                "Sets": row['sets'],
                "Time (sec)": row['time'],
                "Date": row['created_at']
            }
            for row in history_rows
        ]

        df = pd.DataFrame(arr)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            agg_df = df.groupby(["Exercise", "Date"]).agg({
                "Reps": 'sum',
                "Sets": "sum",
                "Time (sec)": "sum"
            }).reset_index()
            agg_df.index += 1
            st.table(agg_df, border="horizontal")
        else:
            st.info("No workout history found.")






 # This ensures the script only runs if it's executed directly, 
# not if it's imported as a module elsewhere.
if __name__ == "__main__":
    main()


    