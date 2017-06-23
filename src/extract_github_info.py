from github import Github
import os
from PIL import Image
import requests
import math
from snakemake.utils import makedirs
import random
import datetime
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
import pandas as pd


configfile: "config.yaml"

# connect to GitHub
g = Github(config["github"])
# extract the Galaxy Training Material repository
repo = g.get_user("galaxyproject").get_repo("tools-iuc")
creation_date = repo.created_at


def format_date(date):
    '''
    Format date to put it at the correct year (going from 1st of July)
    '''
    year_date = date
    year_date = year_date.replace(month = 7)
    year_date = year_date.replace(day = 1)
    year_date = year_date.replace(hour = 0)
    year_date = year_date.replace(minute = 0)
    year_date = year_date.replace(second = 1)
    if date.month < 7:
        year_date = year_date.replace(year = (date.year) - 1)
    return year_date


# generate a data range with month (first day of the month)
data_range = pd.date_range(
    format_date(creation_date),
    format_date(datetime.datetime.now() + relativedelta(years=1)),
    freq=pd.tseries.offsets.DateOffset(years=1))


rule all:
    input:
        contributors="images/contributors.png",
        contributions_table = "data/contributions.csv"


def extract_resizing_value(x, y, n):
    '''
    Extracting the resizing value using the algo in
    https://math.stackexchange.com/questions/466198/algorithm-to-get-the-maximum-size-of-n-squares-that-fit-into-a-rectangle-with-a

    x: width of the rectangle
    y: height of the rectangle
    n: number of square to fit in the (x,y) rectangle
    '''
    px = math.ceil(math.sqrt(n*x/y))
    py = math.ceil(math.sqrt(n*y/x))
    if math.floor(px*y/x)*px < n:
        sx = y/math.ceil(px*y/x)
    else:
        sx = x/px
    if math.floor(py*x/y)*py < n:
        sy = x/math.ceil(x*py/y)
    else:
        sy = y/py
    return math.floor(max(sx, sy))


rule extract_contributor_avatar:
    '''
    Create an image composed of the avatar of all the contributors
    '''
    output:
        contributors="images/contributors.png"
    run:
        avatar_paths = []
        avatar_dir = os.path.join("images", "avatars")
        makedirs(avatar_dir)
        # parse the contributors
        for contri in repo.get_contributors():
            # get the url to the avatar
            avatar_url = contri.avatar_url
            # download the avatar with requests
            avatar_path = os.path.join(avatar_dir, "%s.png" % contri.login)
            if not os.path.exists(avatar_path):
                r = requests.get(avatar_url, stream=True)
                r.raise_for_status()
                with open(avatar_path, "ab") as fd:
                    for chunk in r.iter_content(chunk_size=128):
                        fd.write(chunk)
            # add the path to the list of image paths
            avatar_paths.append(avatar_path)
        # create image to combine the avatars
        result = Image.new("RGB", (config["width"], config["height"]))
        # extract the resizing value
        img_nb = len(avatar_paths)
        print("img nb: %s" % img_nb)
        new_size = extract_resizing_value(
            config["width"],
            config["height"],
            img_nb)
        print("new size: %s" % new_size)
        # extract the number of row and number of column
        col_nb = math.floor(config["width"] / new_size)
        row_nb = math.floor(config["height"] / new_size)
        print("col: %s, row: %s" % (col_nb, row_nb))
        # compute extra pixels
        extra_left_right_pixels = config["width"] - col_nb*new_size
        extra_top_down_pixels = config["height"] - row_nb*new_size
        print("top-down: %s, left-right: %s" % (extra_top_down_pixels, extra_left_right_pixels))
        d_left = math.ceil(extra_left_right_pixels/2)
        d_top = math.ceil(extra_top_down_pixels/2)
        # find how many rectangles will be empty
        empty_rect_nb = col_nb*row_nb - img_nb
        # add as many empty path as many empty rectangles
        avatar_paths += [""] * empty_rect_nb
        # randomize the list of path
        random.shuffle(avatar_paths)
        # resize and add avatar
        for index, filename in enumerate(avatar_paths):
            # if empty path: add nothing
            if not os.path.exists(filename):
                continue
            # load and resize the image
            img = Image.open(filename)
            resized_img = img.resize((new_size, new_size))
            # extract the position of the image in the rectangle
            x = index // row_nb * new_size + d_left
            y = index % row_nb * new_size + d_top
            # add the image
            result.paste(resized_img, (x, y, x + new_size, y + new_size))
        # export the image
        result.save(str(output.contributors))


def format_date_string(date):
    '''
    Format date to a string
    '''
    s = "%s/%s - %s/%s" % (date.month, date.year, date.month-1, date.year+1)
    return s


rule extract_contribution_number:
    '''
    Extract the number of contributions (commits, PR and issues) over the years
    '''
    output:
        contribution_tab = "data/contributions.csv"
    run:
        # extract the contributions per year
        df = pd.DataFrame(
            0,
            columns=["commit_nb","pull_request", "issue"],
            index=data_range)
        # extract the number of commits
        for commit in repo.get_commits():
            date = format_date(commit.commit.author.date)
            df.iloc[df.index.get_loc(date, method='nearest')].commit_nb += 1
        # extract the number of Pull Requests (all: open and closed ones)
        for pr in repo.get_pulls(state="all"):
            date = format_date(pr.created_at)
            df.iloc[df.index.get_loc(date, method='nearest')].pull_request += 1
        # extract the number of Issues (all: open and closed ones)
        for issue in repo.get_issues(state="all"):
            # not counting the issues that are PR
            if issue.pull_request is not None:
                continue
            date = format_date(issue.created_at)
            df.iloc[df.index.get_loc(date, method='nearest')].issue += 1
        # format the date
        df.index = df.index.map(format_date_string)
        # export to file
        df.to_csv(
            str(output.contribution_tab),
            index = True)

