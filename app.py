from datetime import datetime, timedelta
import re
from sqlalchemy import desc, and_
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import json
import googleapiclient.discovery
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# Create Flask app instance and configure database uri
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
scheduler = BackgroundScheduler()


#                               Define Models for video and api data


class VideoMetaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(200))
    thumbnail = db.Column(db.String(200))
    publishedAt = db.Column(db.DateTime)
    channelTitle = db.Column(db.String(100))


class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(60))
    limit_exceed = db.Column(db.Boolean, default=False)


#                                 Background scheduler for API to hit every 10 second


def insert_video_metadata(snippet):
    try:
        video_data = VideoMetaData.query.filter_by(title=snippet['title']).first()
        published_time = datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%S%z')
        if not video_data:
            data = VideoMetaData(
                title=snippet['title'],
                description=snippet['description'],
                thumbnail=snippet['thumbnails']['default']['url'],
                publishedAt=published_time,
                channelTitle=snippet['channelTitle']
            )
            db.session.add(data)
            db.session.commit()
            print("inserted")
        return json.dumps({
            "response": "Video Data Inserted successfully",
            "status": True
        })
    except Exception as e:
        print(e)
        db.session.rollback()
        return json.dumps({
            "response": "Database rollback: Unable to execute insertion.",
            "status": False
        })


def youtube_api_caller():
    local_time = datetime.now(timezone.utc).astimezone() - timedelta(hours=20, minutes=0, seconds=0)
    latest = local_time.isoformat()
    api_keys = APIKey.query.filter_by(limit_exceed=False).first()
    if not api_keys:
        return json.dumps({
            "message": "No API keys available",
            "status": False
        })
    try:
        youtube_obj = googleapiclient.discovery.build("youtube", "v3", developerKey=api_keys.api_key)
        request_data = youtube_obj.search().list(
            part="snippet",
            maxResults=5,
            q="football",
            publishedAfter=latest
        )
        response = request_data.execute()
    except Exception as e:
        print(e)
        api_keys.limit_exceed = True
        db.session.commit()
        return json.dumps({
            "message": "API keys exceeded the quota",
            "status": False
        })
    if len(response["items"]) > 0:
        for video_info in response['items']:
            snippet = video_info['snippet']
            insert_video_metadata(snippet)
        return json.dumps({
            "response": "Added video data for football",
            "status": True
        })
    else:
        return json.dumps({
            "response": "No new videos to be inserted",
            "status": False
        })


#                                               APIs starting here


@app.route('/')
def youtube_home():
    return 'Welcome to the app!'


@app.route('/api/get_video_data/', methods=['GET'])
def get_video_data():
    try:
        # paginate the result
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        sort_type = request.args.get('sort_type', 'Descending')
        if sort_type == 'Descending':
            video_data = VideoMetaData.query.order_by(desc('publishedAt')).paginate(page=page, per_page=per_page)
        elif sort_type == 'Ascending':
            video_data = VideoMetaData.query.order_by('publishedAt').paginate(page=page, per_page=per_page)
        else:
            return jsonify({'Message': 'Wrong sort type input',
                            'status': '404 Bad request'})
        data = []
        for info in video_data.items:
            data.append({'title': info.title, 'description': info.description, 'publishedAt': info.publishedAt,
                         'thumbnails': info.thumbnail, 'channelTitle': info.channelTitle})
        meta = {
            "page": video_data.page,
            'pages': video_data.pages,
            'total_count': video_data.total,
            'prev_page': video_data.prev_num,
            'next_page': video_data.next_num,
            'has_next': video_data.has_next,
            'has_prev': video_data.has_prev,
        }
        return jsonify({"data": data, "meta": meta, "status": 'success'})
    except Exception as e:
        print(e)
        return jsonify({
            'message': 'Error occurred while fetching video data',
            'status': 'Failed',
        })


@app.route('/api/search', methods=['GET'])
def search_video():
    try:
        # Extract words from query text for advance query
        text = request.args.get('text')
        word_list = re.sub("[^\w]", " ", text).split()
        result = []
        for word in word_list:
            term = ("%" + word + "%")
            response = db.engine.execute(
                "SELECT * FROM video_meta_data WHERE title LIKE (?) OR description LIKE (?)",
                (term, term))
            if response:
                result = result + [dict(row) for row in response]
        if not result:
            return jsonify({
                'message': 'No result found',
                'status': 'success'
            })
        result = list({item['id']: item for item in result}.values())
        return jsonify({"data": result, "status": 'success'})
    except Exception as e:
        print(e)
        return jsonify({
            'message': 'Error occurred while searching the video data',
            'status': 'Failed'
        })


@app.route('/api/filter/', methods=['GET'])
def filter_data():
    try:
        # Start date and end date to filter the video data
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({
                "message": "Bad Request, start date or end date not define",
                "status": "Success"
            })
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(hours=24, minutes=0, seconds=0)
        if start_date >= end_date:
            return jsonify({
                "message": "Bad Request, start date is ahead of end date",
                "status": "Success"
            })
        result = VideoMetaData.query.filter(
            and_(VideoMetaData.publishedAt >= start_date, VideoMetaData.publishedAt <= end_date))
        data = []
        for info in result:
            data.append({'title': info.title, 'description': info.description, 'publishedAt': info.publishedAt,
                         'thumbnails': info.thumbnail, 'channelTitle': info.channelTitle})
        if not data:
            return jsonify({
                "message": "No data found for this query",
                "status": "success"
            })
        return jsonify({"data": data, "status": "Success"})
    except Exception as e:
        print(e)
        return jsonify({
            "message": "Error occurred while filtering the data",
            "status": "Failed"
        })


if __name__ == '__main__':
    print("Server started")
    scheduler.add_job(youtube_api_caller, 'interval', seconds=10)
    scheduler.start()
    app.run(debug=True, host='0.0.0.0', port=5050)
