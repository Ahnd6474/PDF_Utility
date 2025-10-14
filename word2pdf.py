from docx2pdf import convert

# All .docx in input_dir -> PDFs in output_dir
convert("Serway 10E Solution/", "Serway Solution/")  # Windows example
# or on macOS/Linux paths
# convert("/Users/you/docs/word", "/Users/you/exports/pdf_out")
