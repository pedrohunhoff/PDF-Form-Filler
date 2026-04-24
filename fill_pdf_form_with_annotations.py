import io
import json
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def transform_from_image_coords(bbox, image_width, image_height, pdf_width, pdf_height):
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height

    left = bbox[0] * x_scale
    right = bbox[2] * x_scale

    top = pdf_height - (bbox[1] * y_scale)
    bottom = pdf_height - (bbox[3] * y_scale)

    return left, bottom, right, top


def transform_from_pdf_coords(bbox, pdf_height):
    left = bbox[0]
    right = bbox[2]

    pypdf_top = pdf_height - bbox[1]      
    pypdf_bottom = pdf_height - bbox[3]   

    return left, pypdf_bottom, right, pypdf_top


def fill_pdf_form(input_pdf_path, fields_json_path, output_pdf_path):
    
    with open(fields_json_path, "r", encoding="utf-8") as f:
        fields_data = json.load(f)
    
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    
    pdf_dimensions = {}
    for i, page in enumerate(reader.pages):
        mediabox = page.mediabox
        pdf_dimensions[i + 1] = (float(mediabox.width), float(mediabox.height))
    
    # Group fields by page number
    fields_by_page = {}
    for field in fields_data["form_fields"]:
        page_num = field["page_number"]
        if page_num not in fields_by_page:
            fields_by_page[page_num] = []
        fields_by_page[page_num].append(field)
    
    text_count = 0
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        pdf_width, pdf_height = pdf_dimensions[page_num]
        
        if page_num in fields_by_page:
            # Create a reportlab overlay with the text drawn directly on it
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
            
            for field in fields_by_page[page_num]:
                if "entry_text" not in field or "text" not in field["entry_text"]:
                    continue
                entry_text = field["entry_text"]
                text = entry_text["text"]
                if not text:
                    continue
                
                page_info = next(p for p in fields_data["pages"] if p["page_number"] == page_num)
                
                if "pdf_width" in page_info:
                    transformed_entry_box = transform_from_pdf_coords(
                        field["entry_bounding_box"],
                        pdf_height
                    )
                else:
                    image_width = page_info["image_width"]
                    image_height = page_info["image_height"]
                    transformed_entry_box = transform_from_image_coords(
                        field["entry_bounding_box"],
                        image_width, image_height,
                        pdf_width, pdf_height
                    )
                
                font_size = entry_text.get("font_size", 14)
                font_color = entry_text.get("font_color", "000000")
                
                left, bottom, right, top = transformed_entry_box
                
                c.setFont("Times-Roman", font_size)
                c.setFillColor(HexColor("#" + font_color))
                c.drawString(left, bottom, text)
                text_count += 1
            
            c.save()
            packet.seek(0)
            
            # Merge the overlay onto the original page
            overlay_reader = PdfReader(packet)
            page.merge_page(overlay_reader.pages[0])
        
        writer.add_page(page)
        
    with open(output_pdf_path, "wb") as output:
        writer.write(output)
    
    print(f"Successfully filled PDF form and saved to {output_pdf_path}")
    print(f"Added {text_count} text entries")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: fill_pdf_form_with_annotations.py [input pdf] [fields.json] [output pdf]")
        sys.exit(1)
    input_pdf = sys.argv[1]
    fields_json = sys.argv[2]
    output_pdf = sys.argv[3]
    
    fill_pdf_form(input_pdf, fields_json, output_pdf)
