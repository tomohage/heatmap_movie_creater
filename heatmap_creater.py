#!/usr/bin/env python
# -*- coding: utf-8 -*-
import heatmap
import csv
import os
import glob
import sys
import shutil

from PIL import Image, ImageDraw



_MONITOR_SIZE_ROW = 2
_POSITION_DATA_ROW = 5

_TRIGGER_OFF_STATUS = 0
_TRIGGER_ON_STATUS = 1


# 指定したfpsで動画を作成できない場合はException
def validate_fps(csv_file_path, fps):
    unit_time = 1.0 / fps * 1000

    csv_file = open(csv_file_path, 'rb')
    csv_reader = csv.reader(csv_file)

    previous_time = None
    time = None
    min_unit_time = None
    row_num = 0
    for row in csv_reader:
        if row_num > _POSITION_DATA_ROW:
            if time is None:
                time = float(row[0])
                continue
            previous_time = time
            time = float(row[0])
            if min_unit_time is None or min_unit_time > time - previous_time:
                min_unit_time = time - previous_time
                if unit_time < min_unit_time:
                    csv_file.close()
                    raise Exception('[Invalid] This fps is too large.')
        row_num += 1
    csv_file.close()


def create_heatmap_movie(csv_file_name, fps, window_size):
    current_dir_path = os.getcwd()

    validate_fps(current_dir_path + '/' + csv_file_name, fps)

    csv_file = open(current_dir_path + '/' + csv_file_name, 'rb')
    csv_reader = csv.reader(csv_file)
    os.makedirs(current_dir_path + "/images")

    # fpsから時系列の時間間隔単位を取得
    unit_time = 1.0 / fps * 1000

    print("fps:" + str(fps) + " unit time:" + str(unit_time) + "[ms]")
    print("create heatmap images")

    file_num = 0
    row_num = 1
    monitor_size = None
    now_time = 0
    pts = []

    # ヒートマップの連番画像を作成
    for row in csv_reader:
        if row_num == _MONITOR_SIZE_ROW:
            monitor_size = [int(float(row[3])), int(float(row[1]))]
            print monitor_size
        elif row_num > _POSITION_DATA_ROW:
            time = float(row[0])
            x = int(float(row[1]))
            y = monitor_size[1] - int(float(row[2]))
            if len(pts) == window_size:
                del (pts[0])
            pts.append([x, y])
            if now_time > time:
                continue
            now_time = int(now_time + unit_time)
            hm = heatmap.Heatmap()
            img = hm.heatmap(
                points = pts,
                size = monitor_size,
                dotsize = 100,
                area = ((0, 0), (monitor_size[1], monitor_size[0])),
                scheme = 'classic',
                opacity = 150
            )
            print(str(now_time) + "[ms] complete")
            img.save(current_dir_path + "/images/PNG%05d.png" % file_num)
            file_num += 1
        row_num += 1
    csv_file.close()

    files = glob.glob(current_dir_path + '/images/*.png')

    i = 0
    for f in files:
        os.rename(f, current_dir_path + '/images/%05d.png' % i)
        i += 1

    cmd = 'ffmpeg -r ' + str(fps) + ' -i images/%05d.png -pix_fmt yuv420p -vcodec libx264 heatmap_movie.mp4'
    os.system(cmd)
    shutil.rmtree('images/')

    print("finish creating movie file.")

def create_heatmap_images(csv_file_name, fps, window_size):
    current_dir_path = os.getcwd()
    if os.name == 'nt':
        validate_fps(current_dir_path + '¥¥' + csv_file_name, fps)
        os.makedirs(current_dir_path + "¥¥images")
    else:
        validate_fps(current_dir_path + '/' + csv_file_name, fps)
        os.makedirs(current_dir_path + "/images")
    # fpsから時系列の時間間隔単位を取得
    unit_time = 1.0 / fps * 1000

    print("fps:" + str(fps) + " unit time:" + str(unit_time) + "[ms]")
    print("create heatmap images")

    file_num = 0
    row_num = 1
    monitor_size = None
    now_time = 0

    # 視点座標の円形図を出力するためのlist
    pts = []
    # ヒートマップを出力するためのlist
    heatmap_pts = []

    count = 0
    time = 0
    if os.name == 'nt':
        csv_file = open(current_dir_path + '¥¥' + csv_file_name, 'rb')
    else:
        csv_file = open(current_dir_path + '/' + csv_file_name, 'rb')
    csv_reader = csv.reader(csv_file)
    for row in csv_reader:
        if row_num > _POSITION_DATA_ROW:
            count += 1
            time = float(row[0])
        row_num += 1
    span = float(time) / float(count)
    csv_file.close()

    # ヒートマップの連番画像を作成
    if os.name == 'nt':
        csv_file = open(current_dir_path + '¥¥' + csv_file_name, 'rb')
    else:
        csv_file = open(current_dir_path + '/' + csv_file_name, 'rb')
    csv_reader = csv.reader(csv_file)
    row_num = 1
    status = _TRIGGER_OFF_STATUS
    for row in csv_reader:
        if row_num == _MONITOR_SIZE_ROW:
            monitor_size = [int(float(row[1])), int(float(row[3]))]
        elif row_num > _POSITION_DATA_ROW:
            file_num += 1
            if len(row) < 4:
                status = _TRIGGER_OFF_STATUS
                continue

            time = float(row[0])
            if now_time > time:
                continue
            if status == _TRIGGER_OFF_STATUS and str.strip(row[3]) == 'T':
                now_time = int(time)
                status = _TRIGGER_ON_STATUS
            else:
                now_time = int(now_time + unit_time)

            if len(pts) == window_size:
                del (pts[0])
                del (heatmap_pts[0])

            heatmap_pts.append([int(float(row[1])), monitor_size[1] - int(float(row[2]))])
            pts.append([int(float(row[1])), int(float(row[2]))])

            hm = heatmap.Heatmap()
            img = hm.heatmap(
                points = heatmap_pts,
                size = (monitor_size[0], monitor_size[1]),
                dotsize = 200,
                area = ((0, 0), (monitor_size[0], monitor_size[1])),
                scheme = 'classic',
                opacity = 200
            )

            dr = ImageDraw.Draw(img, 'RGBA')

            # windowsサイズにある視点を追従する形で出力する
            # 現在の視点座標を一番大きくする
            count = 0
            end = len(pts) - 1
            for pt in pts:
                if count == end:
                    ellipse_size = 60
                else:
                    ellipse_size = 20
                dr.ellipse(
                    (
                        int(float(pt[0])) - ellipse_size / 2,
                        int(float(pt[1])) - ellipse_size / 2,
                        int(float(pt[0])) + ellipse_size / 2,
                        int(float(pt[1])) + ellipse_size / 2
                    ),
                    outline = (255, 255, 255, 200),
                    fill = (255, 255, 255, 200)
                )
                if count != 0:
                    dr.line(
                        (
                            int(float(pts[count - 1][0])),
                            int(float(pts[count - 1][1])),
                            int(float(pts[count][0])),
                            int(float(pts[count][1]))
                        ),
                        fill = (255, 255, 255, 200),
                        width = 5
                    )
                count += 1

            del dr

            print(str(now_time) + "[ms] complete")
            # 時系列の時間をファイル名にして画像ファイルを出力
            # ms単位で10桁でファイル名を設定
            if os.name == 'nt':
                img.save(current_dir_path + "¥¥images¥¥%010d.png" % int(now_time))
            else:
                img.save(current_dir_path + "/images/%010d.png" % int(now_time))
        row_num += 1
    csv_file.close()

    print("finish creating image files and dir.")

    return span


if __name__ == "__main__":
    csv_file = 'recording_data.csv'
    fps = 5
    window_size = 10
    #create_heatmap_movie(csv_file, fps, window_size)
    create_heatmap_images(csv_file, fps, window_size)