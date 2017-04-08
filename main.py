#coding=utf-8
import cv2
import glob
import os
import sys
from PIL import Image
import numpy
import shutil

import heatmap_creater

# PILを使って画像を合成
def overlayOnPart(src_image, overlay_image, posX, posY):

    # オーバレイ画像のサイズを取得
    ol_height, ol_width = overlay_image.shape[:2]

    # OpenCVの画像データをPILに変換
    #　BGRAからRGBAへ変換
    src_image_RGBA = cv2.cvtColor(src_image, cv2.COLOR_BGR2RGB)
    overlay_image_RGBA = cv2.cvtColor(overlay_image, cv2.COLOR_BGRA2RGBA)

    #　PILに変換
    src_image_PIL=Image.fromarray(src_image_RGBA)
    overlay_image_PIL=Image.fromarray(overlay_image_RGBA)

    # 合成のため、RGBAモードに変更
    src_image_PIL = src_image_PIL.convert('RGBA')
    overlay_image_PIL = overlay_image_PIL.convert('RGBA')

    # 同じ大きさの透過キャンパスを用意
    tmp = Image.new('RGBA', src_image_PIL.size, (255, 255, 255, 0))
    # 用意したキャンパスに上書き
    tmp.paste(overlay_image_PIL, (posX, posY), overlay_image_PIL)
    # オリジナルとキャンパスを合成して保存
    result = Image.alpha_composite(src_image_PIL, tmp)

    # COLOR_RGBA2BGRA から COLOR_RGBA2BGRに変更。アルファチャンネルを含んでいるとうまく動画に出力されない。
    return  cv2.cvtColor(numpy.asarray(result), cv2.COLOR_RGBA2BGR)

def resize_image(image, height, width):

    # 元々のサイズを取得
    org_height, org_width = image.shape[:2]
    # 大きい方のサイズに合わせて縮小
    height_ratio = float(height) / org_height
    width_ratio = float(width) / org_width
    resized = cv2.resize(image, (int(width), int(height)))

    return resized

if __name__ == "__main__":
    args = sys.argv
    if len(args) != 6:
        print u"引数を以下のように定義してください"
        print u"1: アイトラッカーの録画CSVファイルのパス"
        print u"2: 録画動画のファイルパス"
        print u"3: ヒートマップ開始の時刻[ms]"
        print u"4: 出力ファイルの名前"
        print u"5: 音無し版のファイルも残しておくフラグ(1を指定)"
        exit()
    recording_csv_path = str(args[1])
    recording_movie_path = str(args[2])
    heatmap_start_ms = int(args[3])
    output_file_name = str(args[4])
    is_saved_movie_no_sound = str(args[5])

    # ヒートマップ画像作成
    heatmap_fps = 5
    window_size = 10
    print u"##### START CREATING HEATMAP IMAGE #####"
    heatmap_creater.create_heatmap_images(recording_csv_path, heatmap_fps, window_size)
    print u"##### FINISH CREATING HEATMAP IMAGE #####"

    current_dir_path = os.getcwd()
    files = glob.glob(current_dir_path + '/images/*.png')
    start_file, ext = os.path.splitext(os.path.basename(files[0]))
    end_file, ext = os.path.splitext(os.path.basename(files[-1]))
    span = (float(end_file) - float(start_file)) / len(files)

    # 読み込む
    cmd = 'ffmpeg -i ' + recording_movie_path + ' -r 30 -ss ' + str(heatmap_start_ms / 1000.0) + ' temp_cut_movie.m4v'
    os.system(cmd)
    cmd = 'ffmpeg -i temp_cut_movie.m4v -vn temp_cut_aud.mp4'
    os.system(cmd)

    movie = cv2.VideoCapture('temp_cut_movie.m4v')
    fps = int(round(movie.get(cv2.cv.CV_CAP_PROP_FPS), 0))
    width = movie.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
    height = movie.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)
    total_frame = movie.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)

    # コーデックの指定
    fourcc = cv2.cv.CV_FOURCC('m', 'p', '4', 'v')

    # 保存ファイルとフレームレートとサイズの指定
    out = cv2.VideoWriter('no_sound_'+ output_file_name, int(fourcc), fps, (int(width), int(height)))
    if movie.isOpened() == True:
        ret, frame = movie.read()
    else:
        ret = False

    print u"##### START CREATING HEATMAP MOVIE #####"
    print u"0[%%] (0/%d)" % total_frame
    percent_count = 1
    frame_count = 0
    while ret:
        frame_count += 1
        now_ms = float(movie.get(cv2.cv.CV_CAP_PROP_POS_MSEC))
        if frame_count == int(percent_count * 0.1 * total_frame):
            print u"%d[%%] (%d/%d)" % ((percent_count * 10), frame_count, total_frame)
            percent_count += 1

        if int(now_ms / span) < len(files):
            heatmap_img_path = files[int(now_ms / span)]
            heatmap_img = cv2.imread(heatmap_img_path, cv2.IMREAD_UNCHANGED)
            heatmap_img = resize_image(heatmap_img, height, width)
            frame = overlayOnPart(frame, heatmap_img, 0, 0)
            rgba = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
            # 書き出し
            out.write(frame)
            cv2.imshow('frame', frame)

        if frame_count == total_frame:
            break
        ret, frame = movie.read()
    movie.release()
    out.release()
    cv2.destroyAllWindows()
    print u"##### FINISH CREATING HEATMAP MOVIE #####"

    # 音声付加
    cmd = 'ffmpeg -i no_sound_' + output_file_name + ' -i temp_cut_aud.mp4 -vsync -1 ' + output_file_name
    os.system(cmd)

    # いらないファイルの削除
    os.remove('temp_cut_movie.m4v')
    os.remove('temp_cut_aud.mp4')
    if is_saved_movie_no_sound != '1':
        os.remove('no_sound_' + output_file_name)

    shutil.rmtree('images/')
