import streamlit as st
import math

st.title("Dam Breach Estimation - Froehlich Method")

failure_mode = st.selectbox("Select Failure Mode", ["Piping", "Overtopping"])
Dv = st.number_input("Volume of Reservoir (acre-ft)", value=100.0)
Dh = st.number_input("Dam Breach Head (ft)", value=10.0)

KVAL = 1.0 if failure_mode == "Piping" else 1.4
bwfVal = round(3.28 * (0.1803 * (KVAL * ((Dv * 1233) ** 0.32) * ((Dh * 0.3048) ** 0.19))))

st.subheader(f"Estimated Breach Width: {bwfVal} ft")
