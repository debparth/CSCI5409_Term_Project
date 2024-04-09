import streamlit as st
import requests
import json
import logging
import base64
import pandas as pd


# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def send_document_to_lambda_s3(file):
    """
    Sends a document and queries to AWS Lambda (csci5409_proj_lambda_s3) via an API Gateway endpoint.
    """
    API_ENDPOINT = 'https://umpg12ojh0.execute-api.us-east-1.amazonaws.com/default/csci5409_proj_lambda_s3'
    headers = {'Content-Type': 'application/pdf'}

    # Convert file content to bytes
    file_content = file.read()

    # Encode file content to base64
    file_content_base64 = base64.b64encode(file_content).decode('utf-8')

    # Extract file name
    file_name = file.name

    logging.info("Sending document to Lambda S3...")
    payload = {
        'body': file_content_base64,
        'filename': file_name,
    }

    response = requests.post(API_ENDPOINT, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to process the document")
        return {"error": f"Error {response.status_code}: {response.text}"}


def send_document_to_lambda(s3_uri, queries_config):
    """
    Sends an S3 URI and queries to AWS Lambda via an API Gateway endpoint and handles the response.
    """
    API_ENDPOINT = 'https://umpg12ojh0.execute-api.us-east-1.amazonaws.com/default/csci5409_proj_lambda'
    headers = {'Content-Type': 'application/json'}

    print(f"Sending document to Lambda: {s3_uri}")
    payload = json.dumps({
        's3_uri': s3_uri,
        'queries_config': queries_config
    })

    response = requests.post(API_ENDPOINT, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to process the document")
        return {"error": f"Error {response.status_code}: {response.text}"}

def display_dataframes(response_body):
    if response_body:
        response_json = json.loads(response_body)

        # Key-Value Pairs
        key_value_pairs = pd.DataFrame(response_json['keyValuePairs'])
        if not key_value_pairs.empty:
            st.subheader("Key-Value Pairs")
            st.dataframe(key_value_pairs)

        # Tables
        tables = pd.DataFrame(response_json['tables'])

        # Identifying unique tables
        table_markers = ['Date:', 'Item']
        marker_indices = tables[tables['Text'].isin(table_markers)].index.tolist()

        # Create a list of DataFrames, each representing a table
        table_dfs = []
        start_index = 0
        for end_index in marker_indices[1:] + [len(tables)]:
            fill_df = tables.iloc[start_index:end_index].pivot_table(index='RowIndex', columns='ColumnIndex', values='Text', aggfunc=' '.join).fillna('')
            table_dfs.append(fill_df)
            start_index = end_index

        if not tables.empty:
            st.subheader("Tables")
            for table_df in table_dfs:
                st.dataframe(table_df)

        # Queries
        queries = pd.DataFrame(response_json['queries'])
        if not queries.empty:
            st.subheader("Queries")
            st.dataframe(queries)

def main():
    st.title("Document Analysis App")

    uploaded_file = st.file_uploader("Upload Document", type=['pdf', 'docx', 'txt'])
    queries = [
        {'Text': 'What is the total amount due?'},
        {'Text': 'What is the due date?'}
    ]

    if st.button('Analyze Document'):
        if uploaded_file is not None:
            st.write("Sending document for analysis...")
            result = send_document_to_lambda_s3(uploaded_file)
            if 'error' in result:
                st.error(f"Failed to upload document to S3: {result['error']}")
            else:
                # Get s3_uri from the response
                logging.info("Received response from Lambda S3")
                logging.info(result)
                s3_uri = json.loads(result['body'])['s3_uri']
                result = send_document_to_lambda(s3_uri, queries)
                if 'error' in result:
                    st.error(f"Processing error: {result['error']}")
                else:
                    st.success("Document processed successfully")
                    st.json(result)
                    display_dataframes(result['body'])  # Display different sections as dataframes

        else:
            st.error("Please enter a valid S3 URI.")

if __name__ == '__main__':
    main()
