import streamlit as st
#import math
import pandas as pd
import numpy as np
import altair as alt
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.title("Dam Break Rules of Thumb")
st.markdown("Based on dambrk_rules_of_thumb.py from LMRFC")

# Inputs
col1, col2 = st.columns(2)

with col1:
    dam_type = st.selectbox("Dam Type", ["Earthen", "Concrete Gravity", "Concrete Arch"])
    Dh_ft = st.number_input("Breach Head (ft)", min_value=0.0, value=30.0, step=1.0)    

with col2:
    failure_mode = st.selectbox("Failure Mode", ["Piping", "Overtopping"])
    Dv_acft = st.number_input("Reservoir Volume (acre-ft)", min_value=0.0, value=1000.0, step=10.0)

downstream_mileage = st.number_input("Downstream Point of Interest (mi)", min_value=0, value=10, step=1)

# Constants and conversions
Dv_m3 = Dv_acft * 1233.48  # Convert to cubic meters
Dh_m = Dh_ft * 0.3048  # Convert to meters

# Froehlich breach width
K = 1.0 if failure_mode == "Piping" else 1.4
Bf = 3.28 * (0.1803 * (K * (Dv_m3 ** 0.32) * (Dh_m ** 0.19)))  # in feet

# Von Thun & Gillette breach width
Bv = 1.5 * Dh_ft  # in feet

# MacDonald & Langridge-Monopolis breach width (example formula)
dam_type_bw = {"Earthen":3, "Concrete Gravity":5, "Concrete Arch":0.9}
#Bm = (0.5 * math.log10(Dv_m3)) + (0.6 * Dh_ft) + 0.5  # in feet
Bm = dam_type_bw[dam_type] * Dh_ft

# Breach Formation Time (converted to minutes)
Tf_froehlich = 0.00254 * (Dv_m3 ** 0.53) * (Dh_m ** -0.90) * 60
Tf_von_thun = 0.0178 * (Dh_m ** 1.4) * 60
Tf_smpdbk = 0.0179 * (Dv_m3 ** 0.37) * 60

# Peak outflow estimates
Qp_froehlich = 0.607 * (Dv_m3 ** 0.295) * (Dh_m ** 1.24)       # m³/s
Qp_von_thun = 3.1 * Bv * (Dh_ft ** 1.5)                        # ft³/s
Qp_smpdbk = 1.4 * (Dv_acft ** 0.5) * (Dh_ft ** 1.5)            # ft³/s

# Convert Froehlich Qp from m³/s to ft³/s
Qp_froehlich_cfs = Qp_froehlich * 35.3147

# Round results
results = {
    "Method": ["Froehlich", "MacDonald (SMPDK)","Von Thun & Gillette" ],
    "Breach Width (ft)": [round(Bf, 2),round(Bm, 2),round(Bv, 2)],
    "Formation Time (hr)": [round(Tf_froehlich, 2), round(Tf_smpdbk, 2), round(Tf_von_thun, 2)],
    "Peak Outflow (cfs)": [round(Qp_froehlich_cfs, 2), round(Qp_smpdbk, 2),round(Qp_von_thun, 2)]
}


# Prepare downstream forecast based on method from OHD (provided by Lee Larson)
#Note: Unless Ht is observed and reported, it may be estimated as 40% the breach head.

results_dstrm = []
for method_name, q_peak in [
    ("Froehlich", Qp_froehlich),
    ("Von Thun & Gillette", Qp_von_thun),
    ("SMPDBK", Qp_smpdbk),
]:
    for mile in range(0, downstream_mileage + 1):
        Qd = 10 ** (np.log10(q_peak) - 0.03 * mile)
        depth = 10 ** (np.log10(Dh_ft * .4 ) - 0.03 * mile) # same logic as before
        results_dstrm.append({
            "Method": method_name,
            "Mile": mile,
            "Peak Discharge (cfs)": round(Qd, 2),
            "Estimated Depth (ft)": round(depth, 2)
        })

downstream_df = pd.DataFrame(results_dstrm)

df = pd.DataFrame(results)

st.markdown("#### Results")
st.dataframe(df, use_container_width=True, hide_index=True)
#st.markdown(results)

# Prepare Altair-compatible data
plot_df = downstream_df.copy()
plot_df["Mile"] = plot_df["Mile"].astype(int)

# Peak Discharge Plot
st.markdown("#### 📉 Peak Discharge vs. Distance")
chart_q = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X('Mile:O', title='Distance Downstream (miles)'),
    y=alt.Y('Peak Discharge (cfs):Q'),
    color='Method:N'
).properties(width=700, height=350)
st.altair_chart(chart_q, use_container_width=True)
st.markdown("Wave Height in Downstream calculations is assumed to be 40% of Dam Breach head")

# Estimated Depth Plot
st.markdown("#### 📈 Estimated Depth vs. Distance")
chart_h = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X('Mile:O', title='Distance Downstream (miles)'),
    y=alt.Y('Estimated Depth (ft):Q'),
    color='Method:N'
).properties(width=700, height=350)
st.altair_chart(chart_h, use_container_width=True)

st.markdown("---")
st.markdown("This tool is based on empirical methods for estimating dam breach parameters. \n To be updated with equations and assumptions.")
