from pdf_convert_to_json import pdf_to_json
from attribute_write import write_attribute

pdf_path = r'Plant Pdf\CKS1138 Ranabima Royal College\GGC_S_0038 - Ranabima Royal College_Project.VC4-Report.pdf'
data=pdf_to_json(pdf_path)
# with open('data.txt', 'w') as f:
#     f.write(str(data))

