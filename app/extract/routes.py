from flask import render_template, request, jsonify, session, redirect, url_for
from app.extract import bp
from app.utils import openai, load_dotenv

@bp.route('/extract_content', methods=['POST'])
def extract_content():
    try:
        schema = request.form.get('schema')
        table_html = request.form.get('table_html')
        
        if not schema or not table_html:
            return jsonify({"error": "Missing schema or table HTML"}), 400
            
        prompt = f"""Based on the following Schema and html table, 
extract ALL content from the table and convert it to json. 
Do not truncate or summarize the data - include every row from the table.
Return the complete dataset as valid JSON that matches the schema structure.

Schema:
{schema}

HTML Table:
{table_html}

Important: Return the complete JSON for all rows. Do not use ellipsis (...) or truncate the data."""
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=12000  # Increased max_tokens
        )
        
        content = response.choices[0].message.content
        
        # Try to parse and format the JSON
        try:
            # Remove any explanatory text before or after the JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', content)
            if json_match:
                content = json_match.group()
            
            parsed_content = json.loads(content)
            pretty_content = json.dumps(parsed_content, indent=2)
        except json.JSONDecodeError:
            pretty_content = content
            
        return render_template('extract/extract.html', content=pretty_content)
        
    except Exception as e:
        print(f"Error in extract_content route: {str(e)}")
        return jsonify({"error": f"Error extracting content: {str(e)}"}), 500
