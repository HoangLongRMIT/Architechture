
import os
from flask import Flask, render_template,jsonify, request, redirect, url_for, send_file, make_response, send_from_directory, send_file, jsonify,render_template_string
from werkzeug.utils import secure_filename
import firebase_admin
import datetime
from firebase_admin import credentials
from firebase_admin import storage
from doctest1 import *

# Initialize Firebase Admin SDK
cred = credentials.Certificate('privateKey.json')

firebase_admin.initialize_app(cred, {
    'storageBucket': 'uploadjs-7f8e6.appspot.com'
})

app = Flask(__name__)

app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = r'temp'  # replace with your upload directory

@app.route('/')
def main():
   return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/checking')
def check():
    return render_template('download.html')
@app.route('/userDetail')
def userDetail():
    return render_template('userDetail.html')

@app.route('/download', methods=['POST'])
def download():
    if request.method == 'POST':
        data = request.form['sub'] 
        # Get the bucket that the files are stored in
        bucket = storage.bucket()

        # List all files in the bucket
        blobs = bucket.list_blobs(prefix=data)

        # Generate a download URL for each file
        files = []
        for blob in blobs:
            print(blob.name)
            files.append({
                'name': blob.name,
                'url': blob.generate_signed_url(datetime.timedelta(seconds=300), method='GET')
            })

        # Render a template with the files
        return jsonify({"files": files})
    
@app.route('/deletefire', methods=['POST'])
def deletefire():
    if request.method == 'POST':
        name = request.form['name'] 
        # Get the bucket that the files are stored in
        bucket = storage.bucket()

        blob = bucket.blob(name)
        blob.delete()

       

        # Render a template with the files
        return jsonify({"status": "success", "message": "File deleted successfully"})
@app.route('/download2', methods=['GET'])
def download2():
    if request.method == 'GET':
        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], "document_updated.docx")
        return send_file(output_filepath, as_attachment=True)
    
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part in the request.'
        
        file = request.files['file']
        data = request.form['sub'] 
        print(data) 
        if file.filename == '':
            return 'No selected file.'
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Upload file to Firebase Storage
            bucket = storage.bucket()
            blob = bucket.blob(data + "/" + filename)
            blob.upload_from_filename(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # response = make_response('', 204)
    # Construct the full file path
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Define the API endpoint for code generation
            api_url = "https://polite-horribly-cub.ngrok-free.app/generate_code?max_length=512"


            # Load the Word document
            word_replacer = WordReplacer(file_path)
            
            underline_finder = WordUnderlineFinder()
            underlined_text_array = underline_finder.collect_underlined_text(word_replacer.docx)

            # Extract all paragraphs from the document
            paragraphs = []
            for paragraph in word_replacer.docx.paragraphs:
                if is_real_reference(paragraph)==False:
                    print(paragraph.text)
                    break
                if paragraph.text!="": paragraphs.append(paragraph.text)
            
            table_texts = []
            for table in word_replacer.docx.tables:
                for row in table.rows:
                    row_text = [cell.text for cell in row.cells]
                    for text in row_text:
                        table_texts.append(text)

            # Create a list of prompts
            prompts_list = []
            for paragraph in paragraphs:
                if not paragraph.strip():  # Skip empty
                    continue
                prompt = f"Correct English in the following text \"{paragraph}.\" \n Corrected version must follows these requirement:\n 1. keep it in one paragraph\n2. do not change curly brackets\n3.do not add space after text\n4.do not add anything after colon\n5. return only the text no explain needed\n"
                for underlined_text in underlined_text_array:
                    if underlined_text in paragraph:
                        prompt += f"Don't change: {underlined_text}\n"
                prompt += "Here is the corrected version: "
                prompts_list.append(prompt)

            prompts_list_table = []
            filtered_table_texts = []

            for table_text in table_texts:
                ignore_this_prompt = any(underlined_text in table_text for underlined_text in underlined_text_array)

                if not ignore_this_prompt:
                    table_prompt = f"Correct English in the following phrase keep it a phrase: {table_text}\nHere is the corrected version: "
                    prompts_list_table.append(table_prompt)
                    filtered_table_texts.append(table_text)

            # Update the original table_texts list
            table_texts = filtered_table_texts
                
            all_prompts_list = prompts_list + prompts_list_table
            
            max_prompts_per_request = 40
            all_text = paragraphs + table_texts
            # Split prompts into chunks of max_prompts_per_request
            prompt_chunks = [all_prompts_list[i:i + max_prompts_per_request] for i in range(0, len(all_prompts_list), max_prompts_per_request)]
            corrected_paragraphs = []
            for i, prompts_chunk in enumerate(prompt_chunks, start=1):
                print(f"Sending request for chunk {i}...")
                # Define API parameters
                api_params = {'prompts': prompts_chunk}
                
                # Send a GET request to the API
                response = requests.get(api_url, params=api_params)
                print (response.status_code)
                # Check the status code and response content
                if response.status_code == 200:
                    corrected_paragraphs.extend(response.json())  # append the response to the list

            # Replace original paragraphs with corrected paragraphs
            for i, (original, corrected) in enumerate(zip(all_text, corrected_paragraphs), start=1):
                word_replacer.replace_in_paragraph(original, corrected.strip())
                word_replacer.replace_in_table(original, corrected.strip())
                print(f"Paragraph {i}: Replaced successfully!")        
                print(corrected.strip())        
            
            # Save the document with replaced paragraphs
            output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], "document_updated.docx")
            word_replacer.save(output_filepath)
            url = blob.generate_signed_url(datetime.timedelta(seconds=300), method='GET')
            print(f"Saved updated document to: {output_filepath}\n")
            send_from_directory(app.config['UPLOAD_FOLDER'], "document_updated.docx", as_attachment=True)
            
                    # Check if the file exists and is accessible
            if os.path.exists(output_filepath) and os.access(output_filepath, os.R_OK):
                print("yes")
                
                return jsonify({"url": url})
            else:
                return "File not found or not accessible", 404
            #os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
            
    else: return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
    app.run(host='0.0.0.0')
