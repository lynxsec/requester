from flask import Flask, render_template, request, jsonify
import base64
import httpx
from requests_toolbelt.multipart import decoder
import asyncio

app = Flask(__name__)
async def complete_send_request():
    try:
        req_data = request.json
        encoded_data = req_data.get('data')
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')

        # Parse the HTTP request
        request_lines = decoded_data.split('\n')
        method, path, protocol = request_lines[0].split(' ')
        headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:] if ': ' in line}
        body_index = decoded_data.index('\n\n') if '\n\n' in decoded_data else len(decoded_data)
        body = decoded_data[body_index:].strip()
        domain = headers.get('Host')
        url = f'https://{domain}{path}'

        # Check if HTTP/2 is required
        client = httpx.AsyncClient(http2=True)

        # Determine request type and handle multipart/form-data
        headers_lower = {k.lower(): v for k, v in headers.items()}
        if 'content-type' in headers_lower:
            if 'multipart/form-data' in headers_lower['content-type']:
                multipart_data = decoder.MultipartDecoder(body.encode(), headers_lower['content-type'])
                body = {part.name: part.content for part in multipart_data.parts}
            # For other content types, use body as is
        else:
            body = body if body else None

        # Sending the HTTP request
        # print(method, url, headers, body)
        try:
            response = await client.request(method, url, headers=headers, data=body)
            print(response)
        except httpx.RequestError as e:
            # If HTTPS fails, retry with HTTP
            url = f'http://{domain}{path}'
            response = await client.request(method, url, headers=headers, data=body)
        except httpx.HTTPError as http_err:
            # Fallback to HTTP/1.1 or provide a more detailed error message
            error_response = f"HTTP error occurred: {http_err}"
            return jsonify({"Error": True, "Response": error_response})
        except Exception as e:
            error_response = f"An error occurred: {e}"
            return jsonify({"Error": True, "Response": error_response})

        # Format the response
        # formatted_response = {
        #     'status_code': response.status_code,
        #     'headers': dict(response.headers),
        #     'body': response.text,
        #     'version': response.http_version
        # }

        response_string = f"{response.http_version} {response.status_code} {response.reason_phrase}\n"
        for key, value in response.headers.items():
            response_string += f"{key}: {value}\n"
        response_string += f"\n{response.text}"

        print(response_string)

        return jsonify({"Error": False, "Response": response_string})
    except Exception as e:
        error_response = f"An error occurred: {e}"
        return jsonify({"Error": True, "Response": error_response})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send-request', methods=['POST'])
async def send_request():
    # asyncio.run(complete_send_request())
    return await complete_send_request()

if __name__ == '__main__':
    app.run(debug=True)