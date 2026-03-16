"""
Data extraction service for structured information from PDFs
Based on existing extraction logic from pdf_convert_to_json.py
"""
import re
from typing import Dict, Any, List, Optional

from ..utils.exceptions import ExtractionError
from ..utils.logger import logger


class DataExtractor:
    """Service for extracting structured data from PDF text"""
    
    def __init__(self):
        """Initialize data extractor"""
        self.logger = logger
        self.sections = [
            "PVsyst - Simulation report",
            "Results summary",
            "General parameters",
            "Array losses",
            "Main results",
            "Loss diagram",
            "P50 - P90 evaluation"
        ]
    
    def extract_structured_data(self, full_text: str) -> Dict[str, Any]:
        """
        Extract structured data from PDF text
        
        Args:
            full_text: Complete text content from PDF
            
        Returns:
            Dictionary containing extracted structured data
        """
        try:
            data = {}
            
            # Break down text into sections
            section_data = self._section_breakdown(full_text, self.sections)
            
            # Extract data from different sections
            if "PVsyst - Simulation report" in section_data:
                data.update(self._extract_plant_details(section_data["PVsyst - Simulation report"]))
            
            if "General parameters" in section_data:
                data.update(self._extract_general_parameters(section_data["General parameters"]))
            
            if "Array losses" in section_data:
                data.update(self._extract_array_losses(section_data["Array losses"]))
                data.update(self._extract_wiring_losses(section_data["Array losses"]))
            
            # Remove None values for cleaner output
            data = {k: v for k, v in data.items() if v is not None}
            
            self.logger.info(f"Successfully extracted {len(data)} fields from PDF")
            return data
            
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            raise ExtractionError(f"Failed to extract structured data: {str(e)}")
    
    def _section_breakdown(self, text: str, sections: List[str]) -> Dict[str, str]:
        """
        Break down text into named sections
        
        Args:
            text: Full text content
            sections: List of section headers to split on
            
        Returns:
            Dictionary mapping section names to their content
        """
        section_data = {}
        pattern = "(" + "|".join(map(re.escape, sections)) + ")"
        parts = re.split(pattern, text)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                section_name = parts[i]
                section_text = parts[i + 1].strip()
                section_data[section_name] = section_text
        
        return section_data
    
    def _extract_plant_details(self, text: str) -> Dict[str, Any]:
        """Extract basic plant/project details"""
        data = {}
        
        try:
            # Project name
            match = re.search(r'Project:\s*(.+)', text)
            if match:
                data["Project"] = match.group(1).strip()
            
            # System power
            match = re.search(r'System power:\s*([\d.]+\s*kWp)', text)
            if match:
                data["System power"] = float(match.group(1).strip().replace(' kWp', ''))
            
            # Coordinates
            match = re.search(r'Longitude\s*([\d.]+)', text)
            if match:
                data["Longitude"] = float(match.group(1).strip())
            
            match = re.search(r'Latitude\s*([\d.]+)', text)
            if match:
                data["Latitude"] = float(match.group(1).strip())
            
            match = re.search(r'Altitude\s*([\d.]+)', text)
            if match:
                data["Altitude"] = float(match.group(1).strip())
            
            # Albedo
            match = re.search(r'Albedo\s*([\d.]+)', text)
            if match:
                data["Albedo"] = float(match.group(1).strip())
            
            # Module count
            match = re.search(r'Nb\. of modules\s*([\d,]+)', text)
            if match:
                data["Nb. of modules"] = int(match.group(1).replace(',', '').strip())
            
            # Nominal power
            match = re.search(r'Pnom total\s*([\d.]+)', text)
            if match:
                data["Pnom total"] = float(match.group(1).strip())
            
            # Inverter details
            match = re.search(r'Nb\. of units\s*([\d]+)', text)
            if match:
                data["Inverter Units"] = int(match.group(1).strip())
            
            match = re.search(r'Total power\s*([\d.]+)', text)
            if match:
                data["Inverter Power"] = float(match.group(1).strip())
            
            match = re.search(r'Pnom ratio\s*([\d.]+)', text)
            if match:
                data["Pnom ratio"] = float(match.group(1).strip())
        
        except Exception as e:
            self.logger.warning(f"Error extracting plant details: {str(e)}")
        
        return data
    
    def _count_arrays(self, text: str) -> int:
        """Count number of arrays in the text"""
        arrays = re.findall(r"Array\s+#\d+", text)
        return len(arrays)
    
    def _extract_general_parameters(self, text: str) -> Dict[str, Any]:
        """Extract general parameters including array and equipment info"""
        data = {}
        
        try:
            no_arrays = self._count_arrays(text)
            data['no_arrays'] = no_arrays
            
            # Split by array sections
            array_blocks = re.split(r"Array\s+#\d+", text)
            
            # Extract array-specific data
            for i in range(1, min(no_arrays + 1, len(array_blocks))):
                array_text = array_blocks[i]
                
                # Tilt and Azimuth
                tilt_az_match = re.search(r'Tilt/Azimuth\s*([\d.-]+)\s*/\s*([\d.-]+)', array_text)
                if tilt_az_match:
                    data[f"Array {i} Tilt"] = int(float(tilt_az_match.group(1).strip()))
                    data[f"Array {i} Azimuth"] = int(float(tilt_az_match.group(2).strip()))
                
                # Number of modules
                match = re.search(r'Number of PV modules\s*([\d,]+)', array_text)
                if match:
                    data[f"Array {i} Number of PV modules"] = int(match.group(1).replace(',', '').strip())
            
            # Extract manufacturers and models
            general_data = array_blocks[0] if array_blocks else text
            
            mfg_match = re.search(
                r"Manufacturer\s+(.+?)\s+Manufacturer\s+(.+?)\s+Model",
                general_data,
                re.S
            )
            if mfg_match:
                data["pv_module_manufacturer"] = mfg_match.group(1).strip()
                data["inverter_manufacturer"] = mfg_match.group(2).strip()
            
            model_match = re.search(
                r"Model\s+([A-Za-z0-9\-_.]+)\s+Model\s+([A-Za-z0-9\-_.]+)",
                general_data,
                re.S
            )
            if model_match:
                data["pv_module_model"] = model_match.group(1).strip()
                data["inverter_model"] = model_match.group(2).strip()
            
            # Unit PV power
            match = re.search(r"Unit Nom\. Power\s+([\d.]+)\s*Wp", general_data)
            if match:
                data["unit_pv_power"] = float(match.group(1).strip())
            
            # Module area (from last block)
            if len(array_blocks) > no_arrays:
                total_data = array_blocks[no_arrays]
                match = re.search(r"Module area\s+([\d.]+)", total_data)
                if match:
                    data["Module area"] = float(match.group(1).strip())
        
        except Exception as e:
            self.logger.warning(f"Error extracting general parameters: {str(e)}")
        
        return data
    
    def _extract_array_losses(self, text: str) -> Dict[str, Any]:
        """Extract array loss data"""
        data = {}
        
        try:
            # Soiling losses
            match = re.search(
                r"Array Soiling Losses.*?Loss Fraction\s*([\d.]+)\s*%",
                text,
                re.S
            )
            if match:
                data["soiling_loss_pct"] = match.group(1)
            
            # LID - Light Induced Degradation
            match = re.search(
                r"LID\s*-\s*Light Induced Degradation.*?Loss Fraction\s*([\d.]+)\s*%",
                text,
                re.S
            )
            if match:
                data["lid_loss_pct"] = match.group(1)
            
            # Module quality loss
            match = re.search(
                r"Module Quality Loss.*?Loss Fraction\s*([-\d.]+)\s*%",
                text,
                re.S
            )
            if match:
                data["module_quality_loss_pct"] = match.group(1)
            
            # Module mismatch losses
            match = re.search(
                r"Module mismatch losses.*?Loss Fraction\s*([\d.]+)",
                text,
                re.S
            )
            if match:
                data["module_mismatch_loss_pct"] = match.group(1)
            
            # IAM (Incidence Angle Modifier) values
            values = [float(v) for v in re.findall(r"\b(1\.000|0\.\d{3})\b", text)]
            angles = [float(a) for a in re.findall(r"(\d+)°", text)]
            
            # Ensure same length
            min_len = min(len(angles), len(values))
            if min_len > 0:
                data["iam_values"] = values[:min_len]
                data["iam_angles"] = angles[:min_len]
        
        except Exception as e:
            self.logger.warning(f"Error extracting array losses: {str(e)}")
        
        return data
    
    def _extract_wiring_losses(self, text: str) -> Dict[str, Any]:
        """Extract wiring loss data"""
        data = {}
        
        try:
            # DC wiring losses
            match = re.search(r"DC wiring losses.*?Loss Fraction\s*([\d.]+)\s*%", text, re.S)
            if match:
                data["dc_wiring_loss_pct"] = match.group(1)
            
            # AC wiring losses
            match = re.search(r"AC wiring losses.*?Loss Fraction\s*([\d.]+)\s*%", text, re.S)
            if match:
                data["ac_wiring_loss_pct"] = match.group(1)
        
        except Exception as e:
            self.logger.warning(f"Error extracting wiring losses: {str(e)}")
        
        return data
    
    def transform_to_attributes(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw extracted data into formatted attributes structure
        
        Args:
            raw_data: Raw extracted data from extract_structured_data
            
        Returns:
            Formatted attributes dictionary
        """
        def to_float(val, default=0.0):
            """Safely convert value to float"""
            try:
                return float(val)
            except (TypeError, ValueError):
                return default
        
        def get_building_type(project_name: str) -> str:
            """Determine building type from project name"""
            if not project_name:
                return "Unknown"
            if "_S_"   in project_name:
                return "School"
            elif "_H_" in project_name:
                return "Hospital"
            elif "_L_" in project_name:
                return "Library"
            return "Other"
        
        def setup_orientations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Create orientations array from array data"""
            orientations = []
            no_arrays = data.get("no_arrays", 0)
            
            for i in range(1, no_arrays + 1):
                orientation = {
                    "tilt": data.get(f"Array {i} Tilt"),
                    "azimuth": data.get(f"Array {i} Azimuth"),
                    "name": f"0{i}",
                    "module_count": data.get(f"Array {i} Number of PV modules")
                }
                orientations.append(orientation)
            
            return orientations
        
        # Parse Project into Site_ID and Site_Name
        project = raw_data.get("Project", "")
        site_id = ""
        site_name = ""
        
        if project and "-" in project:
            parts = project.split("-", 1)
            site_id = parts[0].strip()
            site_name = parts[1].strip() if len(parts) > 1 else ""
        
        # Calculate pv_module_area
        pv_module_area = 0.0
        module_area = raw_data.get("Module area")
        nb_modules = raw_data.get("Nb. of modules")
        if module_area and nb_modules:
            try:
                pv_module_area = round(float(module_area) / int(nb_modules), 4)
            except (ValueError, ZeroDivisionError, TypeError):
                pv_module_area = 0.0
        
        # Build transformed attributes
        attributes = {
            "Site_ID": site_id,
            "Site_Name": site_name,
            "buildingType": get_building_type(project),
            "isSite": "true",
            "longitude": raw_data.get("Longitude"),
            "latitude": raw_data.get("Latitude"),
            "altitude": raw_data.get("Altitude"),
            "system_capacity": raw_data.get("System power"),
            "inverter_model": raw_data.get("inverter_model"),
            "inverter_units": raw_data.get("Inverter Units"),
            "inverter_details": f"{raw_data.get('Inverter Units')} x {raw_data.get('inverter_model')}" if raw_data.get('Inverter Units') and raw_data.get('inverter_model') else None,
            "inverter_power": raw_data.get("Inverter Power"),
            "module_count": raw_data.get("Nb. of modules"),
            "orientation": setup_orientations(raw_data),
            "pv_module_model": raw_data.get("pv_module_model"),
            "pv_module_area": pv_module_area,
            "iam": {
                "angles": [str(int(a)) if isinstance(a, (int, float)) else str(a) for a in raw_data.get("iam_angles", [])],
                "values": [str(v) for v in raw_data.get("iam_values", [])]
            },
            "losses": {
                "soiling": to_float(raw_data.get("soiling_loss_pct")) / 100,
                "lid": to_float(raw_data.get("lid_loss_pct")) / 100,
                "module_quality": to_float(raw_data.get("module_quality_loss_pct")) / 100,
                "mismatch": to_float(raw_data.get("module_mismatch_loss_pct")) / 100,
                "dc_wiring": to_float(raw_data.get("dc_wiring_loss_pct")) / 100,
                "ac_wiring": to_float(raw_data.get("ac_wiring_loss_pct")) / 100,
                "albedo": to_float(raw_data.get("Albedo")),
                "far_shading": 1.0
            }
        }
        
        # Remove None values for cleaner output
        attributes = {k: v for k, v in attributes.items() if v is not None}
        
        return attributes


# Create singleton instance
data_extractor = DataExtractor()
