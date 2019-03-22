# coding:utf-8


import cgi
import re


import logging

logger = logging.getLogger()

file_name_pattern = re.compile(r"((.+?)\.(\w+?))\W*$")

DOWNLOAD_COUNT = 0


def get_file_name_from_disposition(content_disposition):
    try:
        _, params = cgi.parse_header(content_disposition)
        if "filename" in params:
            return params["filename"]
        elif "FILENAME" in params:
            return params["FILENAME"]
        elif "filename*" in params:
            return re.split("utf-8'\s+'", params['filename*'], 1, flags=re.IGNORECASE)[1]
        elif "FILENAME*" in params:
            return re.split("utf-8'\s+'", params['FILENAME*'], 1, flags=re.IGNORECASE)[1]
        else:
            return None
    except Exception as e:
        logger.exception("get_file_name error: %s", e)


def write_data(file_path, download_data):
    try:
        with open(file_path, "rb+") as f:
            for start_position, value in download_data:
                f.seek(start_position)
                f.write(value)
    except Exception as e:
        logger.exception("write data fot file error: %s", e)


def write_to_file(f, startpos, data):
    # print("write_to_file fd:{}, pos:{}".format(f.fileno(), startpos))
    try:
        # print("---", f.fileno(),startpos)
        f.seek(startpos)
        f.write(data)
        f.flush()
        f.flush()
        f.flush()
        f.flush()
        # print("*******",f.fileno(),f.tell()-startpos, len(data) )
    except Exception as e:
        logger.exception("write_to_file error: %s", e)
        # print("---tell fd:{}, pos:{} ".format(f.fileno(), f.tell()))


def get_file_name_by_pattern(path):
    try:
        path_params = path.split("/")
        match_names = []
        for p in path_params:
            match = file_name_pattern.search(p)
            if match:
                # print(match.groups())
                match_names.append(match.groups()[0])
        if match_names:
            return match_names[-1]
        return path_params[-1]
    except Exception as e:
        logger.exception("get_file_name_by_pattern error: %s", e)


def open_file(filename):
    try:
        with open(filename, 'w') as tempf:
            tempf.seek(0)
            tempf.write("hello")
    except Exception as e:
        logger.exception("open_file error:%s", e)


def open_file_to_fd(filename):
    try:
        with open(filename, 'w') as tempf:
            tempf.seek(0)
            tempf.write("hello")
    except Exception as e:
        logger.exception("open_file error:%s", e)


def get_utf8_code(encode_format, content):
    try:
        if not encode_format:
            encode_format = 'ISO-8859-1'
        try:
            return content.encode(encode_format).decode('utf-8')
        except UnicodeEncodeError as e:
            return content.encode('ISO-8859-1').decode('utf-8')
    except:
        logger.error("get utf-8 coding error", exc_info=True)

if __name__ == "__main__":
    # url = "http://pic110.huitu.com/pic/20180925/1301968_20180925195933385080_0.jpg"
    url = "https://nodejs.org/dist/v10.13.0/node-v10.13.0-x64.msi"
    from urllib.parse import urlparse
    path = urlparse(url).path
    # print("====")
    print(get_file_name_by_pattern(path))
    #logger.error("gfsdfsdf")