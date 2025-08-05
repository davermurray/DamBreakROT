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

def highlight_by_damtype(value):
    if dam_type == "Earthen" and value == "Froehlich":
        color = f"background-color: lightgreen;"
    elif dam_type != "Earthen" and value == "SMPDBK":
        color = f"background-color: lightgreen;"
    else:
        color = None
    return  color

st.markdown("""
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 0rem;
                    padding-left: 4rem;
                    padding-right: 4rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.markdown("### Dam Break Rules of Thumb")
st.caption("An experimental interface with NID to quickly run the LMRFC ROT.")

# Inputs
Dh_ft_default = 30.0
Dv_acft_default = 1000.0
Dsa_ac_default = 2 * Dv_acft_default/Dh_ft_default
fedId_default = None
dam_type_order = ["Earthen", "Concrete Gravity", "Concrete Arch"]

dam_input = st.text_input("NID Search:",value="")

dam_suggests, search_exception = dam_get(dam_input)
if search_exception:
    st.caption(search_exception)


if isinstance(dam_suggests, dict) and "dams" in dam_suggests.keys() and dam_suggests["dams"]:
    dam_suggestion_df = pd.DataFrame(dam_suggests["dams"]).head(10) #limited to top 10
    damdf_select = st.dataframe(dam_suggestion_df[['name','countyState','federalId']],use_container_width=True, hide_index=True,on_select="rerun",
    selection_mode="single-row") 
   
    if len(damdf_select.selection.rows) > 0:
        fedId_default = dam_suggestion_df.iloc[damdf_select.selection.rows,[3]].values[0][0]
    else:
        fedId_default = dam_suggestion_df.iloc[0,[3]].values[0]
        #st.write('Using top search result: ', fedId_default)
#Set the federal Id - manually or through the search above as default
#fedId = st.text_input("NID Id",value=fedId_default)

st.markdown("#### Rules of Thumb Inputs")

if fedId_default != None: 
    dam_query, exception_msg = dam_inventory(fedId_default)
    if exception_msg:
        st.caption(exception_msg)
  
    dam_df = pd.DataFrame(dam_query, index = [0])
    heightcols = ['hydraulicHeight','nidHeight','damHeight']  
    storagecols= ['maxStorage', 'nidStorage','normalStorage']
    othercols = ['surfaceArea','damLength','structure_types']
    try:
        df_title = "Available NID Data for **" + str(dam_df['name'].values[0]+"("+str(dam_df['federalId'].values[0])+")**")
        st.markdown(df_title)
        heightselect = st.dataframe(dam_df[heightcols],use_container_width=True, hide_index=True,on_select='rerun',selection_mode='multi-column')
        storageselect = st.dataframe(dam_df[storagecols],use_container_width=True, hide_index=True,on_select='rerun',selection_mode='multi-column')
        st.dataframe(dam_df[othercols],use_container_width=True, hide_index=True,on_select='rerun',selection_mode='multi-column')
               
        #Select Height (defaults to max)   
        height_selected = dam_df[heightselect.selection.columns].columns        
        for i in heightcols[::-1]:#go through in reverse so the last is Hydraulic        
            if dam_df[i].values[0] != None:
                Dh_ft_default = dam_df[i].values[0].astype(float)                
                if i in height_selected:   #if selected then break loop                   
                    break
       
        #Select Storage (defaults to max)
        storage_selected = dam_df[storageselect.selection.columns].columns
        for i in storagecols[::-1]:
            if dam_df[i].values[0] != None:
                Dv_acft_default = dam_df[i].values[0].astype(float)
                if i in storage_selected:                
                    break
           
       #surface area - use if provided otherwise calculate from vol and height 
        if dam_df['surfaceArea'].values[0] != None:
            Dsa_ac_default = dam_df['surfaceArea'].values[0].astype(float)
        else:
            Dsa_ac_default = 2 * Dv_acft_default/Dh_ft_default #recalculate based on above

        if dam_df['structure_types'].values[0] != None and str.lower(dam_df['structure_types'].values[0]).find('concrete') >= 0:
            dam_type_order = ["Concrete Gravity", "Concrete Arch", "Earthen"]
    except:
        st.write('No Dam found.')  

    st.caption('Initial Breach Head is set to NID Dam Height, and Reservoir Volume is set to Max Volume. Click on columns in displayed dataframe to use their values instead. Manually edit info in table as needed.')
# Inputs 
   


col1, col2 = st.columns(2)

with col1:
    dam_type = st.selectbox("Dam Type", dam_type_order)         
    failure_mode = st.selectbox("Failure Mode", ["Overtopping","Piping"])
    Dh_ft = st.number_input("Breach Head (ft)", min_value=0.0, value=Dh_ft_default, step=1.0)   
with col2:    
    Dv_acft = st.number_input("Reservoir Volume (acre-ft)", min_value=0.0, value=Dv_acft_default, step=10.0)
    Dsa_ac = st.number_input("Reservoir Surface Area (acres)", min_value=0.0, value=Dsa_ac_default, step=10.0)
    downstream_mileage = st.number_input("Downstream Point of Interest (mi)", min_value=0.0, value=10.0, step=0.1)

with st.expander("Max Tailwater width and Erodibility Inputs"):
    tw_width = st.number_input("Max Tailwater Width (ft) - Arch Dams only ", min_value=0.0, value=100.0, step=1.0)
    erodability = st.selectbox("Dam Erodability - Von Thun Only", ["Erosion Resistant","Easily Erodible"])
#downstream_mileage = st.number_input("Downstream Point of Interest (mi)", min_value=0.0, value=10.0, step=0.1)

lmrfctab ,mbrfctab, tab2, tab3 = st.tabs(["LMRFC", "MBRFC","Travel Time", "Equation Information"])

with lmrfctab: 
    # Constants and conversions
    Dv_m3 = Dv_acft * 1233.48  # Convert to cubic meters - Original rules of thumb uses 1233
    Dh_m = Dh_ft * 0.3048  # Convert to meters

    # Froehlich breach width
    K = 1.0 if failure_mode == "Piping" else 1.4
    Bf = 3.28 * (0.1803 * (K * (Dv_m3 ** 0.32) * (Dh_m ** 0.19)))  # in feet

    # Von Thun & Gillette breach width
    #Bv = 1.5 * Dh_ft  # in feet
    if Dv_m3 < 1233000:
        bw_const = 6.1
    elif (Dv_m3 < 6165000) and (Dv_m3 >= 1233000):
        bw_const = 18.3
    elif (Dv_m3 < 12330000) and (Dv_m3 >= 6165000):
        bw_const = 42.7
    elif Dv_m3 >= 12330000:
        bw_const = 54.9

    #Von Thun breach width
    Bv = round((2.5 * (Dh_m) + bw_const)*3.28,2)

    # MacDonald & Langridge-Monopolis breach width and timing
    dam_type_bw = {"Earthen":[3,10], "Concrete Gravity":[5,40], "Concrete Arch":[0.9,50]}
    #Bm = (0.5 * math.log10(Dv_m3)) + (0.6 * Dh_ft) + 0.5  # in feet
    if dam_type == "Concrete Arch":
        Bm = dam_type_bw[dam_type][0] * tw_width
    else:
        Bm = dam_type_bw[dam_type][0] * Dh_ft

    # Breach Formation Time (converted to minutes)
    Tf_froehlich = 0.00254 * (Dv_m3 ** 0.53) * (Dh_m ** -0.90) * 60

    if erodability == "Erosion Resistant":
        Tf_von_thun = (0.02 * (Dh_m) + 0.25)* 60
    else:
        Tf_von_thun = 0.015 * Dh_m * 60

    Tf_smpdbk = Dh_ft / dam_type_bw[dam_type][1] 

    # Froehlich Peak outflow estimates
    Qp_froehlich = 0.607 * (Dv_m3 ** 0.295) * (Dh_m ** 1.24)       # m³/s
    # Convert Froehlich Qp from m³/s to ft³/s
    Qp_froehlich_cfs = Qp_froehlich * 35.3147 # Original rules of thumb uses 35.31

    #SMPDBK Peak Ouflow from LMRFC ROT 
    smpdbk_const = (23.4 * Dsa_ac)/Bm
    Qp_smpdbk = (3.1 * Bm) * (smpdbk_const/((Tf_smpdbk/60) + smpdbk_const / (Dh_ft**0.5)))**3.0

    # Round results
    results = {
        "Method": ["Froehlich", "SMPDBK","Von Thun & Gillette" ],
        "Breach Width (ft)": [round(Bf, 2),round(Bm, 2),round(Bv, 2)],
        "Formation Time (min)": [round(Tf_froehlich, 2), round(Tf_smpdbk, 2), round(Tf_von_thun, 2)],
        "Peak Outflow (cfs)": [round(Qp_froehlich_cfs, 2), round(Qp_smpdbk, 2),None]
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

    df = pd.DataFrame(results)
    #Convert to strings before the apply map in order to control the decimals to 2
    for i in df.columns[1:]:
        df[i] = df[i].apply(lambda x: '{:.2f}'.format(x))

    #Put a dash where nan (Von Thun PeakOutflow)
    df = df.replace("nan","-")
   
    st.markdown("##### Breach Width, Formation Time, and Peak Q")
    st.caption("Prefered equation highlighted in green based on dam type specified.")
    st.dataframe(df.style.map(highlight_by_damtype,subset=["Method"]), use_container_width=True, hide_index=True)
    #Print downstream Q and height df
    st.markdown("##### Downstream Peak Q and Depth Estimate")
    st.caption("Initial wave height is assumed to be 40% of Dam Breach Head")

    st.dataframe(downstream_df[downstream_df['Mile'] == downstream_mileage],use_container_width=True, hide_index=True)

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
    ).properties(width=700, height=350).configure_legend(orient='top')
    st.altair_chart(chart_q, use_container_width=True)

with mbrfctab:
    st.write('Experimental')
with tab2:
    st.markdown("#### Flood wave Velocity")
    st.write("Flood wave velocity varies across the country depending upon the slope and vegetation density, but some estimates can be made based on historical dam breaks. Except at the dam site, average downstream speeds of a flood wave are in the range of:")
    st.markdown("* 3 to 4 miles per hour for valley areas \n * 5 to 7 miles per hour for foothills\n* 8 to 10 miles per hour for mountainous areas")
    st.markdown("##### Fread Velocity")
    st.latex('c = (0.005/n) * H^{2/3} * S^{1/2}')
    st.caption('where c is the wave velocity, H is the dam breach height,n is Mannings, and S is channel bottom slope (ft/mi)')
    st.write("Using Dam Breach Height (ft): ", Dh_ft)
    manningsn = st.number_input("Manning's n", min_value=0.00, value=0.05, step=0.01)
    slope = st.number_input("Channel slope (ft/mi)", min_value=5.0, value=10.0, step=0.1)

    fread = np.round((0.005/manningsn) * Dh_ft**(2/3) * slope**(0.5),2)
    fread_time = np.round(downstream_mileage / fread,2)

   
    st.write("Fread Velocity (mph): ", fread)
    st.write("Time to downstream point ("+str(np.round(downstream_mileage,2))+" mi) in hours: ", fread_time)
    
    st.markdown("##### OHD Velocity")
    st.caption("See Equation info. Uses Wave Height of 40% of Dam Breach head.")
    ohd_v = np.round(3*(Dh_ft*0.4)**0.33)
    st.write("OHD velocity (mph): ", ohd_v)

#Equation infomation Tabs
with tab3:
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
    with st.expander("Travel Times / Velocity"):
        file_content_fr = read_text_file("docs/frVelocity.hlp")  
        st.markdown(file_content_fr)
        file_content_pf = read_text_file("docs/pfVelocity.hlp")  
        st.markdown(file_content_pf)  

st.markdown("---")
st.markdown("This tool is based on empirical methods for estimating dam breach parameters. \n To be updated with equations and assumptions.")
