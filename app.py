import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests

def read_text_file(file_path):
    with open(file_path, "r") as file:
        return file.read()

def dam_get(input=None):
    query = None
    exception_msg = False
    if input != None or len(input) > 0 or input != "None":        
        try:
            query = requests.get("https://nid.sec.usace.army.mil/api/suggestions?text="+str(input),timeout=5).json()
        except requests.exceptions.Timeout:
            exception_msg = ":red[NID query timed out. Verify NID website is available.]"
        except:
            exception_msg = ":red[Could not connect to NID, enter Dam information manually.]"       
    return query, exception_msg

def dam_inventory(id=None):
    exception_msg = False
    if id != None:
        try:
            #added external_risk inventory to get the structure type as the integer damTypeIds field has no metadata
            inventory = requests.get("https://nid.sec.usace.army.mil/api/dams/"+str(id)+"/inventory").json()
            inventory_external_risk = requests.get("https://nid.sec.usace.army.mil/api/dams/"+str(id)+"/external-risk-inventory").json()
        except requests.exceptions.Timeout:
            exception_msg = ":red[NID query timed out. Verify NID website is available.]"
        except:
            exception_msg = ":red[Could not connect to NID, enter Dam information manually.]"
   
        combined_dict = inventory | inventory_external_risk
        #inventorydf = pd.DataFrame([inventory[inventory_fields], inventory_external_risk[risk_fields]])
    else:
        combined_dict = None
    
    return combined_dict, exception_msg

def dam_external_risk(id=None):
    exception_msg = False
    if id != None:
        try:
            inventory = requests.get("https://nid.sec.usace.army.mil/api/dams/"+str(id)+"/external-risk-inventory").json()
        except requests.exceptions.Timeout:
            exception_msg = ":red[NID query timed out. Verify NID website is available.]"
        except:
            exception_msg = ":red[Could not connect to NID, enter Dam information manually.]"
    else:
        inventory = None
    return inventory

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

st.markdown("## Dam Break Rules of Thumb")
st.markdown("An experimental interface with NID to quickly run the LMRFC ROT.")

# Inputs
Dh_ft_default = 30.0
Dv_acft_default = 1000.0
fedId_default = None
dam_type_order = ["Earthen", "Concrete Gravity", "Concrete Arch"]

dam_input = st.text_input("Dam NID Search:",value="")

dam_suggests, search_exception = dam_get(dam_input)
if search_exception:
    st.caption(search_exception)


if isinstance(dam_suggests, dict) and "dams" in dam_suggests.keys() and dam_suggests["dams"]:
    dam_suggestion_df = pd.DataFrame(dam_suggests["dams"]).head(10) #limited to top 10
    damdf_select = st.dataframe(dam_suggestion_df[['name','countyState','federalId']],use_container_width=True, hide_index=True,on_select="rerun",
    selection_mode="single-row") 
    if len(damdf_select.selection.rows) > 0:
        fedId_default = dam_suggestion_df.iloc[damdf_select.selection.rows,[3]].values[0][0]

#Set the federal Id - manually or through the search above as default
fedId = st.text_input("NID Id",value=fedId_default)

if fedId != None: 
    dam_query, exception_msg = dam_inventory(fedId)
    if exception_msg:
        st.caption(exception_msg)
  
    dam_df = pd.DataFrame(dam_query, index = [0])
    dfcols = ['name','damHeight', 'damLength', 'maxStorage', 'nidHeight','nidStorage','normalStorage','surfaceArea','structure_types','primary_structure_type_id']
    try:
        inputselect = st.dataframe(dam_df[dfcols],use_container_width=True, hide_index=True,on_select='rerun',selection_mode='multi-column')
    #Selecting Columns to use in Equations
        col_names = dam_df[inputselect.selection.columns].columns
        
        #Use nidHeight if selected and valid 
        if 'nidHeight' in col_names and dam_df['nidHeight'].values[0] != None:
            Dh_ft_default = dam_df['nidHeight'].values[0].astype(float)
        elif dam_df['damHeight'].values[0] != None:        
            Dh_ft_default = dam_df['damHeight'].values[0].astype(float)

        #Select Storage (defaults to max)
        if dam_df['maxStorage'].values[0] != None:
            Dv_acft_default = dam_df['maxStorage'].values[0].astype(float)
        for i in ['maxStorage','nidStorage','normalStorage']:
            if i in col_names and dam_df[i].values[0] != None:
                Dv_acft_default = dam_df[i].values[0].astype(float)
                break
                
        if dam_df['structure_types'].values[0] != None and str.lower(dam_df['structure_types'].values[0]).find('concrete') >= 0:
            dam_type_order = ["Concrete Gravity", "Concrete Arch", "Earthen"]
    except:
        st.write('No Dam found.')  
        
col1, col2 = st.columns(2)

with col1:
    dam_type = st.selectbox("Dam Type", dam_type_order)
    Dh_ft = st.number_input("Breach Head (ft)", min_value=0.0, value=Dh_ft_default, step=1.0)    

with col2:
    failure_mode = st.selectbox("Failure Mode", ["Overtopping","Piping"])
    Dv_acft = st.number_input("Reservoir Volume (acre-ft)", min_value=0.0, value=Dv_acft_default, step=10.0)

downstream_mileage = st.number_input("Downstream Point of Interest (mi)", min_value=0.0, value=10.0, step=0.1)

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
#Qp_von_thun = 3.1 * Bv * (Dh_ft ** 1.5)                        # ft³/s
Qp_smpdbk = 1.4 * (Dv_acft ** 0.5) * (Dh_ft ** 1.5)            # ft³/s

# Convert Froehlich Qp from m³/s to ft³/s
Qp_froehlich_cfs = Qp_froehlich * 35.3147

# Round results
results = {
    "Method": ["Froehlich", "SMPDBK","Von Thun & Gillette" ],
    "Breach Width (ft)": [round(Bf, 2),round(Bm, 2),round(Bv, 2)],
    "Formation Time (min)": [round(Tf_froehlich, 2), round(Tf_smpdbk, 2), round(Tf_von_thun, 2)],
    "Peak Outflow (cfs)": [round(Qp_froehlich_cfs, 2), round(Qp_smpdbk, 2),"N/A"]
}


# Prepare downstream forecast based on method from OHD (provided by Lee Larson)
#Note: Unless Ht is observed and reported, it may be estimated as 40% the breach head.

results_dstrm = []
for method_name, q_peak in [
    ("Froehlich", Qp_froehlich_cfs),
   # ("Von Thun & Gillette", Qp_von_thun),
    ("SMPDBK", Qp_smpdbk),
]:
    for mile in np.append(np.arange(0, downstream_mileage,0.1),downstream_mileage):
        Qd = 10 ** (np.log10(q_peak) - 0.03 * mile)
        depth = 10 ** (np.log10(Dh_ft * .4 ) - 0.03 * mile) # same logic as before
        results_dstrm.append({
            "Method": method_name,
            "Mile": mile,
            "Peak Discharge (cfs)": round(Qd, 2),
            "Estimated Depth (ft)": round(depth, 2)
        })

downstream_df = pd.DataFrame(results_dstrm)
#st.dataframe(downstream_df.iloc[-2:],use_container_width=True, hide_index=True) 

df = pd.DataFrame(results)

tab1, tab2 = st.tabs(["Results", "Equation Information"])

def highlight_by_damtype(value):
    if dam_type == "Earthen" and value == "Froehlich":
        color = f"background-color: lightgreen;"
    elif dam_type != "Earthen" and value == "SMPDBK":
        color = f"background-color: lightgreen;"
    else:
        color = None
    return  color#f"border: red;" if dam_type == "Earthen" and value == "Froehlich" else None

with tab1:
    #st.markdown("#### Results")
    st.markdown("##### Breach Width, Formation Time, and Peak Outflow")
    st.caption("Prefered equation highlighted in green based on dam type specified.")
    st.dataframe(df.style.applymap(highlight_by_damtype), use_container_width=True, hide_index=True)
    #Print downstream Q and height df
    st.markdown("##### Downstream Peak Discharge and Height Estimate")
    st.caption("Initial wave height in downstream calculations is assumed to be 40% of Dam Breach Head")

    st.dataframe(downstream_df[downstream_df['Mile'] == downstream_mileage],use_container_width=True, hide_index=True)
#Equation infomation Tabs
with tab2:
    st.write('Below information is taken directly from LMRFC Dam Break ROT')
    with st.expander("Froehlich"):
        file_content_bp = read_text_file("docs/bpFroehlich.hlp")  
        st.markdown(file_content_bp)
        file_content_pf = read_text_file("docs/pfFroehlich.hlp") 
        st.write(file_content_pf)
    with st.expander("Simplified Dam Break"):
        file_content_bp = read_text_file("docs/bpSMPDBK.hlp")  
        st.markdown(file_content_bp)
        file_content_pf = read_text_file("docs/pfSMPDBK.hlp") 
        st.write(file_content_pf)
    with st.expander("Van Thun & Gillete"):
        file_content_bp = read_text_file("docs/bpVTG.hlp")  
        st.markdown(file_content_bp)
    with st.expander("Downstream Peak Discharge and Height"):
        file_content_bp = read_text_file("docs/pfDownstream.hlp")  
        st.markdown(file_content_bp)  



# Prepare Altair-compatible data
plot_df = downstream_df.copy()
plot_df["Mile"] = round(plot_df["Mile"],2)
plot_df['Peak Q Formula'] = plot_df['Method']

# Peak Discharge Plot
st.markdown("#### 📉 Peak Discharge vs. Distance")
chart_q = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X('Mile:O', title='Distance Downstream (miles)'),
    y=alt.Y('Peak Discharge (cfs):Q'),
    color='Peak Q Formula:N'
).properties(width=700, height=350)
st.altair_chart(chart_q, use_container_width=True)

# Estimated Depth Plot
#st.markdown("#### 📈 Estimated Depth vs. Distance")
chart_h = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X('Mile:O', title='Distance Downstream (miles)'),
    y=alt.Y('Estimated Depth (ft):Q'),
    color='Method:N'
).properties(width=700, height=350)
#st.altair_chart(chart_h, use_container_width=True)

st.markdown("---")
st.markdown("This tool is based on empirical methods for estimating dam breach parameters. \n To be updated with equations and assumptions.")
