import streamlit as st

st.set_page_config(page_title="UCL GK Stats", layout="wide")

st.title("UCL GK Stats 📊")
st.info("### 🏗️ Work In Progress")
st.write("This page is currently under development. Come back soon!")

if st.button("Back to Main"):
    st.switch_page("FPL_Main_Info.py")
