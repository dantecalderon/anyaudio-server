import requests
import traceback
import logging
from flask import jsonify, request, render_template, url_for, make_response
from subprocess import check_output, call
from ymp3 import app, LOCAL

from helpers.search import get_videos, get_video_attrs
from helpers.helpers import delete_file, get_ffmpeg_path, get_filename_from_title
from helpers.encryption import get_key, encode_data, decode_data


@app.route('/')
def home():
    return render_template('/home.html')


@app.route('/d/<path:url>')
def download_file(url):
    """
    Download the file from the server.
    First downloads the file on the server using wget and then converts it using ffmpeg
    """
    try:
        # decode info from url
        data = decode_data(get_key(), url)
        vid_id = data['id']
        url = data['url']
        filename = get_filename_from_title(data['title'])
        m4a_path = 'static/%s.m4a' % vid_id
        mp3_path = 'static/%s.mp3' % vid_id
        # ^^ vid_id regex is filename friendly [a-zA-Z0-9_-]{11}
        # download and convert
        command = 'wget -O %s %s' % (m4a_path, url)
        check_output(command.split())
        command = get_ffmpeg_path()
        command += ' -i %s -acodec libmp3lame -ab 128k %s -y' % (m4a_path, mp3_path)
        call(command, shell=True)  # shell=True only works, return ret_code
        data = open(mp3_path, 'r').read()
        response = make_response(data)
        # set headers
        response.headers['Content-Disposition'] = 'attachment; filename=%s' % filename
        response.headers['Content-Type'] = 'audio/mpeg'  # or audio/mpeg3
        response.headers['Content-Length'] = str(len(data))
        # remove files
        delete_file(m4a_path)
        delete_file(mp3_path)
        # stream
        return response
    except Exception:
        logging.error(traceback.format_exc())
        return 'Bad things have happened', 400


@app.route('/g/<path:url>')
def get_link(url):
    """
    Uses youtube-dl to fetch the direct link
    """
    data = decode_data(get_key(), url)
    vid_id = data['id']
    title = data['title']
    command = 'youtube-dl https://www.youtube.com/watch?v=%s -f m4a/bestaudio' % vid_id
    command += ' -g'
    print command
    try:
        retval = check_output(command.split())
        retval = retval.strip()
        if not LOCAL:
            retval = encode_data(get_key(), id=vid_id, title=title, url=retval)
            retval = url_for('download_file', url=retval)
        return jsonify({'status': 0, 'url': retval})
    except Exception:
        return jsonify({'status': 1, 'url': None})


@app.route('/search')
def search():
    """
    Search youtube and return results
    """
    search_term = request.args.get('q')
    link = 'https://www.youtube.com/results?search_query=%s' % search_term
    link += '&sp=EgIQAQ%253D%253D'  # for only video
    r = requests.get(
        link,
        allow_redirects=True
    )
    vids = get_videos(r.content)
    ret_vids = []
    for _ in vids:
        temp = get_video_attrs(_)
        if temp:
            ret_vids.append(temp)
    return jsonify(ret_vids)


# @app.route('/v/<string:vid_id>')
# def get_video(vid_id):
#     """
#     Gets video info ..
#     """
#     data = get_video_info_ydl(vid_id)
#     if len(data) > 0:
#         return jsonify(data)
#     else:
#         return 'There was a problem', 400
