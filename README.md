# YouTube Data API

## Project Goal

To make an API to fetch the latest videos sorted in reverse chronological order of their publishing date-time from YouTube for a given tag/search query in a paginated response.

## Basic Requirements:

- Server should call the YouTube API continuously in background (async) with some interval (say 10 seconds) for fetching the latest videos for a predefined search query and should store the data of videos (specifically these fields - Video title, description, publishing datetime, thumbnails URLs and any other fields you require) in a database with proper indexes.
- A GET API which returns the stored video data in a paginated response sorted in descending order of published datetime.
- A basic search API to search the stored videos using their title and description.
- Dockerize the project.
- It should be scalable and optimised.

## Setup for local development
- Clone the repository:
```
git clone https://github.com/Hardik610/fampay_youtube.git
```
-Then get all the requirements for the project:- 
```pip3 install -r requirements.txt```
-To start the flask server
```python3 app.py```

## Build application
In order to build application, the repository comes with stand-alone Dockerfile. Follow the commands to build the application individually.
```docker build -t fampay_youtube_assignment .```
```docker run -p 8000:5050 fampay_youtube_assignment```

## API Endpoints
To get all videos(GET): "http://localhost:8000/api/get_video_data/"
    -Query Parameters - page:int, per_page:int, sort_type:[Ascending, Descending]
To search with a query(GET): "http://localhost:8000/api/search"
    -Query Parameters - text:any
To filter with range on the basis of publishedAt(GET): "http://localhost:8000/api/filter"
    -Query Parameters - start_date: Date(%y-%m-%d), end_date: Date(%y-%m-%d)
To add YouTube v3 API key(POST): "http://localhost:8000/api/add_key"
    -Body - api_key: key
   