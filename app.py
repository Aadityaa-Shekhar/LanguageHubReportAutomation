import datetime
import logging
import smtplib
import traceback
import threading
import time
from flask import Flask, render_template, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notion_client import Client
from datetime import datetime
import schedule

app = Flask(__name__, template_folder='templates')

# Replace with your SMTP server details
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'tiya.shekhar@gmail.com'
SMTP_PASSWORD = 'glev etui rxjm kxey'  # Make sure to replace this with your actual email password
EMAIL_SOURCE = 'tiya.shekhar@gmail.com'

# Initialize the Notion client with your integration token
notion = Client(auth="secret_QUPkzKMWYCcjWkTlf1b4TmVzJ3Oj2nntuS85Wh9yrg0")

# Replace with your database IDs
GOALS_DB_ID = "16fe615f37624183abba96c8a4b12d76"
CERTIFICATION_DB_ID = "2b15bbfc0ad249a0bf5a07c98134c16f"
VOCAB_DB_IDS = ['952ece35fb8b414186ed2b625ab30a26']
GRAMMAR_DB_IDS = ['cede56e997594b7d8ca77503d25140d3']
DAILY_LOG_DB_ID = '245984f7c95b4c33b2b8e5834f74b89d'
TIME_DIST_DB_ID = '16005549ef2e495fa876e5c9812fa9dc'
DAILY_TIME_SPENT_DB_ID = 'e69ecd6dfa0d4211a228e91168d068be'
WATCHLIST_DB_ID = '95815bfd563c4c5e95608d358f3bbab0'
BOOK_LOG_DB_ID = '4b844fdf0097432aa93ec8d2980013b0'
COMMUNITIES_DB_ID = '600d2525ab9641b99c60d24a6fe32dfa'

properties_to_display = {
    'goals': {
        'Start Date': 'start_date',
        'End Date': 'end_date',
        'Status': 'status',
        'Certification': 'certification',
        'Proficiency Level': 'proficiency_level',
        'Progress': 'progress',
        'Goals': 'goals',
        'Languages': 'languages',
        'Description': 'description',
        'Priority': 'priority',
    },
    'certification': {
        'Certification Name': 'certification_name',
        'Language': 'language',
        'Status': 'status',
        'Completion Date': 'completion_date',
        'Score/Grade': 'score_grade',
        'Organisation': 'organisation',
        'Expiration Date': 'expiration_date',
        'Comment': 'comment',
        'Certifying Body': 'certifying_body',
    },
    'vocabulary': {
        'Gender': 'gender',
        'Prefix': 'prefix',
        'Word': 'word',
        'How to Pronounce': 'how_to_pronounce',
        'Type': 'type',
        'Translation (In your native language)': 'translation',
        'Sentence/Note': 'sentence_note',
        'Root Word': 'root_word',
        'Usage': 'usage',
    },
    'grammar': {
        'Type': 'type',
        'Rule': 'rule',
        'Usage': 'usage',
        'Example': 'example',
    },
    'daily_log': {
        'Description': 'description',
        'Date': 'date',
        'Notes': 'notes',
        'Resource': 'resource',
        'Duration': 'duration',
    },
    'time_distribution': {
        'Language': 'language',
        'Priority': 'priority',
        'Predicted mins/day': 'predicted_mins_day',
        'Predicted hours/week': 'predicted_hours_week',
        'Real Time Spent (hours)': 'real_time_spent_hours',
        'Total Time (hours)': 'total_time_hours',
    },
    'daily_time_spent': {
        'Language': 'language',
        'Date': 'date',
        'Sessions Completed': 'sessions_completed',
        'Session Time (min)': 'session_time_min',
        'Total Time Spent (min)': 'total_time_spent_min',
        'Total Time Spent (hours)': 'total_time_spent_hours',
    },
    'watchlist': {
        'Title': 'title',
        'Watch Date': 'watch_date',
        'Language': 'language',
        'Watched': 'watched',
        'Type': 'type',
        'Genre': 'genre',
        'Rating': 'rating',
    },
    'book_log': {
        'Book Title': 'book_title',
        'Author': 'author',
        'Language': 'language',
        'Status': 'status',
        'Rating': 'rating',
        'Date Finished': 'date_finished',
    },
    'communities': {
        'Partner/Group': 'partner_group',
        'Language': 'language',
        'Type': 'type',
        'Duration (mins)': 'duration_mins',
        'Date': 'date',
        'Session Goals': 'session_goals',
        'Notes': 'notes',
    }
}

def fetch_data_from_notion(database_info):
    def get_database_items(database_id):
        try:
            results = notion.databases.query(database_id=database_id)
            return results.get("results", [])
        except Exception as e:
            logging.error(f"Error fetching database items for {database_id}: {str(e)}")
            return []


    def get_related_names(relation_ids):
        if not relation_ids:
            return 'No related names'
        names = []
        for relation_id in relation_ids:
            try:
                response = notion.pages.retrieve(page_id=relation_id)
                title = response.get('properties', {}).get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', 'Unknown')
                names.append(title)
            except Exception as e:
                names.append(f'Error fetching related name: {str(e)}')
        return ', '.join(names)

    def process_properties(properties, display_names):
        output = []
        for property_name, display_name in display_names.items():
            property_data = properties.get(property_name, {})
            
            if 'rich_text' in property_data:
                rich_text_data = property_data.get('rich_text', [])
                property_value = ', '.join([text['text']['content'] for text in rich_text_data]) if rich_text_data else 'No content'
            elif 'date' in property_data:
                date_data = property_data.get('date', {})
                if date_data:
                    start_date = date_data.get('start', 'Date not set')
                    end_date = date_data.get('end', 'No end date') if date_data.get('end') else ''
                    property_value = f"Start: {start_date} End: {end_date}" if start_date else 'Date not set'
                else:
                    property_value = 'Date not set'
            elif 'number' in property_data:
                property_value = property_data['number']
            elif 'relation' in property_data:
                relation_ids = [rel['id'] for rel in property_data.get('relation', [])]
                property_value = get_related_names(relation_ids)
            elif 'multi_select' in property_data:
                property_value = ', '.join([item['name'] for item in property_data['multi_select']])
            elif 'select' in property_data:
                property_value = property_data['select'].get('name', 'N/A') if property_data['select'] else 'N/A'
            elif 'status' in property_data:
                property_value = property_data['status'].get('name', 'N/A') if property_data['status'] else 'N/A'
            elif 'title' in property_data:
                property_value = ', '.join([text['text']['content'] for text in property_data['title']])
            elif 'rollup' in property_data:
                rollup_data = property_data.get('rollup', {})
                if property_name == 'Progress':
                    number_value = rollup_data.get('number', None)
                    property_value = f"{number_value * 100:.2f}%" if number_value is not None else 'No data'
                elif property_name == 'Certification':
                    array_data = rollup_data.get('array', [])
                    texts = [item['title'][0]['text']['content'] for item in array_data if 'title' in item]
                    property_value = ', '.join(texts) if texts else 'No data'
                elif property_name == 'Real Time Spent (hours)':
                    number_value = rollup_data.get('number', None)
                    property_value = f"{number_value:.2f} hours" if number_value is not None else 'No data'
                else:
                    property_value = 'N/A'
            elif 'formula' in property_data:
                formula_data = property_data.get('formula', {})
                property_value = formula_data.get('number', 'N/A') if 'number' in formula_data else 'N/A'
            else:
                property_value = 'N/A'

            output.append(f"{display_name}: {property_value}")
        return output

    database_ids = [
        GOALS_DB_ID,
        CERTIFICATION_DB_ID,
        *VOCAB_DB_IDS,
        *GRAMMAR_DB_IDS,
        DAILY_LOG_DB_ID,
        TIME_DIST_DB_ID,
        DAILY_TIME_SPENT_DB_ID,
        WATCHLIST_DB_ID,
        BOOK_LOG_DB_ID,
        COMMUNITIES_DB_ID
    ]

    all_data = {}
    for database_id in database_ids:
        database_items = get_database_items(database_id)
        if database_items:
            db_key = database_id
            db_name = None
            if database_id == GOALS_DB_ID:
                db_name = 'goals'
            elif database_id == CERTIFICATION_DB_ID:
                db_name = 'certification'
            elif database_id in VOCAB_DB_IDS:
                db_name = 'vocabulary'
            elif database_id in GRAMMAR_DB_IDS:
                db_name = 'grammar'
            elif database_id == DAILY_LOG_DB_ID:
                db_name = 'daily_log'
            elif database_id == TIME_DIST_DB_ID:
                db_name = 'time_distribution'
            elif database_id == DAILY_TIME_SPENT_DB_ID:
                db_name = 'daily_time_spent'
            elif database_id == WATCHLIST_DB_ID:
                db_name = 'watchlist'
            elif database_id == BOOK_LOG_DB_ID:
                db_name = 'book_log'
            elif database_id == COMMUNITIES_DB_ID:
                db_name = 'communities'

            if db_name:
                all_data[db_name] = []
                for item in database_items:
                    properties = item.get('properties', {})
                    display_data = process_properties(properties, properties_to_display[db_name])
                    all_data[db_name].append(display_data)

    return all_data


@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')


@app.route('/fetch_notion_data', methods=['GET'])
def fetch_notion_data():
    try:
        data = fetch_data_from_notion()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def send_email(recipient_email, subject, message_body):
    if not recipient_email:
        logging.error("No recipient email provided.")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SOURCE
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message_body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login('tiya.shekhar@gmail.com', 'glev etui rxjm kxey')
            server.sendmail(EMAIL_SOURCE, recipient_email, msg.as_string())
        logging.info(f"Email sent to {recipient_email} with subject: {subject}")
        return True
    except smtplib.SMTPException as e:
        logging.error(f"SMTP Error: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Failed to send email to {recipient_email}. Error: {str(e)}")
        return False


@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Get form data
        data = {
            'notion_token': request.form.get('notion_token'),
            'goals_db_id': request.form.get('goals_db_id'),
            'certification_db_id': request.form.get('certification_db_id'),
            'vocab_db_ids': request.form.get('vocab_db_ids'),
            'grammar_db_ids': request.form.get('grammar_db_ids'),
            'daily_log_db_id': request.form.get('daily_log_db_id'),
            'time_dist_db_id': request.form.get('time_dist_db_id'),
            'daily_time_spent_db_id': request.form.get('daily_time_spent_db_id'),
            'watchlist_db_id': request.form.get('watchlist_db_id'),
            'book_log_db_id': request.form.get('book_log_db_id'),
            'communities_db_id': request.form.get('communities_db_id'),
            'recipient_email': request.form.get('recipient_email'),
        }

        logging.info(f"Form data received: {data}")

        # Update Notion client with the new token
        notion = Client(auth=data['notion_token'])

        # Fetch data from Notion
        all_data = fetch_data_from_notion()

        # Prepare email content
        email_subject = "Notion Data Report"
        email_body = "<html><body>"
        for db_name, items in all_data.items():
            email_body += f"<h2 style='font-size:24px; font-weight:bold;'>{db_name.capitalize()} Data</h2>"
            for item in items:
                email_body += '<br>'.join(item) + '<br><br>'

        email_body += "</body></html>"

        logging.info(f"Email body prepared: {email_body}")

        # Send the email
        send_email(data['recipient_email'], email_subject, email_body)

        # Render the HTML page with success message
        return render_template('submit.html', recipient_email=data['recipient_email']), 200
    except Exception as e:
        app.logger.error(f"Error in /submit endpoint: {e}")
        return render_template('submit.html', recipient_email=None), 500


@app.route('/schedule_emails', methods=['POST'])
def schedule_emails():
    try:
        # Collect form data
        notion_token = request.form['notion_token']
        goals_db_id = request.form['goals_db_id']
        certification_db_id = request.form['certification_db_id']
        vocab_db_ids = request.form['vocab_db_ids'].split(',')
        grammar_db_ids = request.form['grammar_db_ids'].split(',')
        daily_log_db_id = request.form['daily_log_db_id']
        time_dist_db_id = request.form['time_dist_db_id']
        daily_time_spent_db_id = request.form['daily_time_spent_db_id']
        watchlist_db_id = request.form['watchlist_db_id']
        book_log_db_id = request.form['book_log_db_id']
        communities_db_id = request.form['communities_db_id']
        recipient_email = request.form['recipient_email']

        if not recipient_email or '@' not in recipient_email:
            logging.error(f"Invalid recipient email: {recipient_email}")
            return render_template('submit.html', recipient_email=None), 400

        # Update Notion client with the new token
        notion = Client(auth=notion_token)

        # Fetch data from Notion
        all_data = fetch_data_from_notion([
            goals_db_id,
            certification_db_id,
            *vocab_db_ids,
            *grammar_db_ids,
            daily_log_db_id,
            time_dist_db_id,
            daily_time_spent_db_id,
            watchlist_db_id,
            book_log_db_id,
            communities_db_id
        ])

        # Prepare email content
        email_subject = "Notion Data Report"
        email_body = "<html><body>"
        for db_name, items in all_data.items():
            email_body += f"<h2 style='font-size:24px; font-weight:bold;'>{db_name.capitalize()} Data</h2>"
            for item in items:
                email_body += '<br>'.join(item) + '<br><br>'

        email_body += "</body></html>"

        logging.info(f"Email body prepared: {email_body}")

        # Send the email
        email_sent = send_email(recipient_email, email_subject, email_body)

        # Render the HTML page with success message
        return render_template('submit.html', recipient_email=recipient_email if email_sent else None)

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return render_template('submit.html', recipient_email=None), 500

def check_and_send_email():
    while True:
        now = datetime.now()
        if now.day == 1:  # Check if it's the 1st of the month
            logging.info("It's the first of the month. Sending report...")
            schedule_emails()
            time.sleep(86400)  # Sleep for 24 hours to avoid sending multiple emails in one day
        time.sleep(3600)  # Check every hour

# Start the background thread when the Flask app starts
thread = threading.Thread(target=check_and_send_email)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    app.run(debug=True)