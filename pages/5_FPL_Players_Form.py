import streamlit as st

st.set_page_config(page_title="FPL Players Form", layout="wide")

st.title("FPL Players Form 📊")
st.info("### 🏗️ Work In Progress")
st.write("This page is currently under development. Come back soon!")

if st.button("Back to Main"):
    st.switch_page("FPL_Main_Info.py")
