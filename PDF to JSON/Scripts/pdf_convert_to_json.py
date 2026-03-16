import pdfplumber
import json
import re


full_text = ""
data={}

sections = [
    "PVsyst - Simulation report",
    "Results summary",
    "General parameters",
    "Array losses",
    "Main results",
    "Loss diagram",
    "P50 - P90 evaluation"
]
section_data = {}


def read_pdf_to_text(pdf_path):
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content += text + "\n"
    return text_content

def section_breakdown(text, sections):
    global section_data
    pattern = "(" + "|".join(map(re.escape, sections)) + ")"
    parts = re.split(pattern, text)
    for i in range(1, len(parts), 2):
        section_name = parts[i]
        section_text = parts[i + 1].strip()
        section_data[section_name] = section_text
    

def extract_plant_details(text):
    global data
    data["Project"] = re.search(r'Project:\s*(.+)', text).group(1).strip()
    data["System power"] = float(re.search(r'System power:\s*([\d.]+\s*kWp)', text).group(1).strip().replace(' kWp', ''))
    data["Longitude"] = float(re.search(r'Longitude\s*([\d.]+)', text).group(1).strip())
    data["Latitude"] = float(re.search(r'Latitude\s*([\d.]+)', text).group(1).strip())
    data["Altitude"] = float(re.search(r'Altitude\s*([\d.]+)', text).group(1).strip())
    data["Albedo"] = float(re.search(r'Albedo\s*([\d.]+)', text).group(1).strip())
    data["Nb. of modules"] = int(re.search(r'Nb\. of modules\s*([\d,]+)', text).group(1).replace(',', '').strip())
    data["Pnom total"] = float(re.search(r'Pnom total\s*([\d.]+)', text).group(1).strip().replace(' kWp', ''))
    data["Inverter Units"] = int(re.search(r'Nb\. of units\s*([\d]+)', text).group(1).strip())
    data["Inverter Power"] = float(re.search(r'Total power\s*([\d.]+)', text).group(1).strip().replace(' kWac', ''))
    data["Pnom ratio"] = float(re.search(r'Pnom ratio\s*([\d.]+)', text).group(1).strip())

def array_count(text):
    arrays = re.findall(r"Array\s+#\d+", text)
    return len(arrays)   

def extract_general_parameters(text):
    global data
    no_arrays = array_count(text)
    data['no_arrays'] = no_arrays
    array_blocks = re.split(r"Array\s+#\d+", text)
    for i in range(1, no_arrays+1):
        array_text = array_blocks[i]
        # Extract tilt/azimuth with flexible format matching
        tilt_az_match = re.search(r'Tilt/Azimuth\s*([\d.-]+)\s*/\s*([\d.-]+)', array_text)
        if tilt_az_match:
            tilt = tilt_az_match.group(1).strip()
            azimuth = tilt_az_match.group(2).strip()
            data[f"Array {i} Tilt"] = int(tilt)
            data[f"Array {i} Azimuth"] = int(azimuth)
        data[f"Array {i} Number of PV modules"] = int(re.search(r'Number of PV modules\s*([\d,]+)', array_text).group(1).replace(',', '').strip())
    genral_data=array_blocks[0]
    total_data=array_blocks[no_arrays]
    # Get PV Array Characteristics section for Module area
    
    
    mfg_match = re.search(
        r"Manufacturer\s+(.+?)\s+Manufacturer\s+(.+?)\s+Model",
        genral_data,
        re.S)
    model_match = re.search(
        r"Model\s+([A-Za-z0-9\-_.]+)\s+Model\s+([A-Za-z0-9\-_.]+)",
        genral_data,
        re.S)

    data["pv_module_manufacturer"] = mfg_match.group(1).strip()
    data["inverter_manufacturer"] = mfg_match.group(2).strip()
    data["pv_module_model"] = model_match.group(1).strip()
    data["inverter_model"] = model_match.group(2).strip()
    data["unit_pv_power"] = float(re.search(r"Unit Nom\. Power\s+([\d.]+)\s*Wp", genral_data).group(1).strip())
    data["Module area"] = float(re.search(r"Module area\s+([\d.]+)", total_data).group(1).strip())


def array_losses(text):
    global data

    soiling = re.search(
        r"Array Soiling Losses.*?Loss Fraction\s*([\d.]+)\s*%",
        text,
        re.S)
    if soiling:
        data["soiling_loss_pct"] = soiling.group(1)
    lid = re.search(
        r"LID\s*-\s*Light Induced Degradation.*?Loss Fraction\s*([\d.]+)\s*%",
        text,
        re.S)
    if lid:
        data["lid_loss_pct"] =lid.group(1)

    module_quality = re.search(
        r"Module Quality Loss.*?Loss Fraction\s*([-\d.]+)\s*%",
        text,
        re.S
        )
    if module_quality:
        data["module_quality_loss_pct"] = module_quality.group(1)

    module_mismatch = re.search(
    r"Module mismatch losses.*?Loss Fraction\s*([\d.]+)",
    text,
    re.S
    )
    if module_mismatch:
        data["module_mismatch_loss_pct"] = module_mismatch.group(1)

    # Extract IAM values and angles from the IAM section
    values = [float(v) for v in re.findall(r"\b(1\.000|0\.\d{3})\b", text)]
    angles = [float(a) for a in re.findall(r"(\d+)°", text)]
    
    # Ensure angles and values have the same length (take minimum to avoid mismatch)
    min_len = min(len(angles), len(values))
    data["iam_values"] = values[:min_len]
    data["iam_angles"] = angles[:min_len]


def wiring_losses(text):
    global data
    data["dc_wiring_loss_pct"] = re.search(r"DC wiring losses.*?Loss Fraction\s*([\d.]+)\s*%", text, re.S).group(1)
    data["ac_wiring_loss_pct"] = re.search(r"AC wiring losses.*?Loss Fraction\s*([\d.]+)\s*%", text, re.S).group(1)

    
def pdf_to_json(pdf_path):
    global data, full_text
    full_text = read_pdf_to_text(pdf_path)
    section_breakdown(full_text, sections)
    extract_plant_details(section_data["PVsyst - Simulation report"])
    extract_general_parameters(section_data["General parameters"])
    array_losses(section_data["Array losses"])
    wiring_losses(section_data["Array losses"])
    return data




    








# data={}

# data["TOTAL DC CAPACITY :- "]=re.search(r'TOTAL DC CAPACITY\s*:-\s*([\d.]+\s*kWp)', full_text).group(1).strip() 
# data["TOTAL AC CAPACITY :- "] = re.search(r'TOTAL AC CAPACITY\s*:-\s*([\d.]+\s*kWac)', full_text).group(1).strip()
# data["TOTAL NO PV MODULES "]= re.search(r'TOTAL NO PV MODULES \(\d+Wp\)\s*:-\s*([\w\(\)\d]+)', full_text).group(1).strip() if re.search(r'TOTAL NO PV MODULES \(\d+Wp\)\s*:-\s*([\w\(\)\d]+)', full_text) else None
# data["STRING ARRANGEMENT :- "]= re.search(r'STRING ARRANGEMENT\s*:-\s*([\d\w\s,X-]+?)(?:\n|$)', full_text).group(1).strip() if re.search(r'STRING ARRANGEMENT\s*:-\s*([\d\w\s,X-]+?)(?:\n|$)', full_text) else None



