import streamlit as st
import math
import pandas as pd

st.title("Dam Breach Width and Time Estimator")

# Inputs
failure_mode = st.selectbox("Failure Mode", ["Piping", "Overtopping"])
Dv_acft = st.number_input("Reservoir Volume (acre-ft)", min_value=0.0, value=1000.0, step=10.0)
Dh_ft = st.number_input("Breach Head (ft)", min_value=0.0, value=30.0, step=1.0)

# Constants and conversions
Dv_m3 = Dv_acft * 1233.48  # Convert to cubic meters
Dh_m = Dh_ft * 0.3048  # Convert to meters

# Froehlich breach width
K = 1.0 if failure_mode == "Piping" else 1.4
Bf = 3.28 * (0.1803 * (K * (Dv_m3 ** 0.32) * (Dh_m ** 0.19)))  # in feet

# Von Thun & Gillette breach width
Bv = 1.5 * Dh_ft  # in feet

# MacDonald & Langridge-Monopolis breach width (example formula)
Bm = (0.5 * math.log10(Dv_m3)) + (0.6 * Dh_ft) + 0.5  # in feet

# Breach Formation Time 
Tf_froehlich = 0.00254 * (Dv_m3 ** 0.53) * (Dh_m ** -0.90) * 60
Tf_von_thun = 0.0178 * (Dh_m ** 1.4) * 60
Tf_smpdbk = 0.0179 * (Dv_m3 ** 0.37) * 60
# Round results
results = {
    "Method": ["Froehlich", "Von Thun & Gillette", "MacDonald (SMPDK)"],
    "Breach Width (ft)": [round(Bf, 2), round(Bv, 2), round(Bm, 2)],
    "Formation Time (hr)": [round(Tf_froehlich, 2), round(Tf_von_thun, 2), round(Tf_smpdbk, 2)]
}

df = pd.DataFrame(results)

st.markdown("### 💡 Results")
st.dataframe(df, use_container_width=True)

st.markdown("---")
st.markdown("This tool is based on empirical methods for estimating dam breach parameters.")
