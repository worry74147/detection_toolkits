"""Object detector inference
@kv
# TODO: cpu & gpu mode switch
"""

import os
import sys
import cv2
import json
import struct

# pip install imagesize
import imagesize

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from os.path import isfile, join
from tqdm import tqdm

import time

import mmcv

from mmdet.apis import init_detector
from mmdet.apis import inference_detector
from mmdet.apis import show_result


def plot_and_save_bboxes(img_arr, bboxes, out_path):
    img_h, img_w, _ = img_arr.shape
    # Create figure and axes
    fig, ax = plt.subplots(1)
    ax.imshow(img_arr.astype(np.uint8))
    for bbox in bboxes:
        bbox[0] = bbox[0] * img_h
        bbox[1] = bbox[1] * img_w
        bbox[2] = bbox[2] * img_h
        bbox[3] = bbox[3] * img_w
        ymin, xmin, ymax, xmax = bbox
        x = int(xmin)
        y = int(ymin)
        w = int(xmax - xmin)
        h = int(ymax - ymin)
        rect = patches.Rectangle(
            (x, y),
            w,
            h,
            linewidth=1,
            edgecolor='r',
            facecolor='none')
        ax.add_patch(rect)
    plt.savefig(out_path)
    plt.clf()


def xyxy2xywh(bbox):
    # bbox is numpy array
    _bbox = bbox.tolist()
    return [
        _bbox[0],
        _bbox[1],
        _bbox[2] - _bbox[0] + 1,
        _bbox[3] - _bbox[1] + 1,
    ]


def format_result(result, conf=0.9):
    outputs = []
    for label in range(len(result)):
        bboxes = result[label]
        for i in range(bboxes.shape[0]):
            score = float(bboxes[i][4])
            if score < conf:
                continue
            data = dict()
            data['bbox'] = xyxy2xywh(bboxes[i])
            data['score'] = score
            data['category_id'] = 1
            outputs.append(data)
    return outputs

def results2json(image_file_names, results, outfile_prefix):
    """Dump the detection results to a json file.

    There are 3 types of results: proposals, bbox predictions, mask
    predictions, and they have different data types. This method will
    automatically recognize the type, and dump them to json files.

    Args:
        results (list[list | tuple | ndarray]): Testing results of the
            dataset.
        outfile_prefix (str): The filename prefix of the json files. If the
            prefix is "somepath/xxx", the json files will be named
            "somepath/xxx.bbox.json", "somepath/xxx.segm.json",
            "somepath/xxx.proposal.json".

    Returns:
        dict[str: str]: Possible keys are "bbox", "segm", "proposal", and
            values are corresponding filenames.
    """

    def _det2json(filenames, results):
        json_results = []
        for img_id, (img_file, result) in enumerate(zip(filenames, results)):
            for label in range(len(result)):
                bboxes = result[label]
                for i in range(bboxes.shape[0]):
                    data = dict()
                    data['image_id'] = img_id
                    data['bbox'] = xyxy2xywh(bboxes[i])
                    data['score'] = float(bboxes[i][4])
                    data['category_id'] = 1
                    json_results.append(data)
        return json_results

    """
    def _proposal2json(filenames, results):
        json_results = []
        for img_id, (img_file, result) in enumerate(zip(filenames, results)):
            bboxes = result
            for i in range(bboxes.shape[0]):
                data = dict()
                data['image_id'] = img_id
                data['bbox'] = xyxy2xywh(bboxes[i])
                data['score'] = float(bboxes[i][4])
                data['category_id'] = 1
                json_results.append(data)
        return json_results
    """
    result_files = dict()
    if isinstance(results[0], list):
        print('LIST')
        json_results = _det2json(image_file_names, results)
        result_files['bbox'] = '{}.{}.json'.format(outfile_prefix, 'bbox')
        result_files['proposal'] = '{}.{}.json'.format(
            outfile_prefix, 'bbox')
        mmcv.dump(json_results, result_files['bbox'])
    else:
        raise TypeError('invalid type of results')
    """
    elif isinstance(results[0], np.ndarray):
        json_results = _proposal2json(image_file_names, results)
        result_files['proposal'] = '{}.{}.json'.format(
            outfile_prefix, 'proposal')
        mmcv.dump(json_results, result_files['proposal'])
    """
    return result_files


def main(args):

    if args.image_dir is None:
        raise ValueError('No input!')
    image_filenames = [f for f in os.listdir(args.image_dir) if isfile(join(args.image_dir, f))]

    if not os.path.exists(args.output_dir) and not args.video_output:
        os.makedirs(args.output_dir)

    config_file = args.config_path
    checkpoint_file = args.model_dir

    model = init_detector(config_file, checkpoint_file, device='cuda:0')

    inference_time = 0.0
    """TODO:
        - Do not save images anymore. (need cooperate with viewer)
        - Save inference results as list of dict to numpy
            a numpy array [Nx7] where each row contains {imageID,x1,y1,w,h,score,class}
        - Support video in, video out.
    """
    # if args.video_format:
    #   video_out = cv2.VideoWriter(args.output_dir, cv2.VideoWriter_fourcc(*'DIVX'), args.fps, (640, 480))

    #results = []
    # COCO annotation container
    json_dict = {
        'images': [],
        'annotations': [],
        'categories': [
            {
            'supercategory': 'person',
            'id': 1,
            'name': 'person',
            }
        ],
    }
    image_id = 1
    bbox_id = 1
    ignore = 0 
    category_id = 1

    for img_file_name in tqdm(image_filenames):
        start_time = time.time()
        img_path = join(args.image_dir, img_file_name)
        result = inference_detector(model, img_path)
        end_time = time.time()
        inference_time += (end_time - start_time)
        output_path = join(args.output_dir, os.path.basename(img_path))

        formated_result = format_result(result, conf=args.confidence)

        img_width, img_height = imagesize.get(img_path)
    
        image_info = {
            'file_name': img_file_name,
            'height': img_height,
            'width': img_width,
            'id': image_id,
            }
        json_dict['images'].append(image_info)

        for res in formated_result:
            bbox = res['bbox']
            category_id = res['category_id']
            xmin, ymin, w, h = bbox

            annotation = {
                'area': w * h,
                'iscrowd': ignore,
                'image_id': image_id,
                'bbox': bbox,
                'category_id': category_id,
                'id': bbox_id,
                'ignore': ignore,
                'segmentation': [],
                }
            json_dict['annotations'].append(annotation)
            bbox_id += 1
        image_id += 1
        #if args.video_output:
        #    pass
        #    # img = show_result(img_path, result, [model.CLASSES], out_file=None, show=False)
        #    # video_out.write(img)
        if not args.no_image:
            show_result(img_path, result, [model.CLASSES], out_file=output_path, show=False)

        #results.append(result)
    prediction_output_path = os.path.join(args.output_dir, os.path.basename(args.config_path).rstrip('.py')) + '.json'
    with open(prediction_output_path, 'w') as json_fp:
        json_str = json.dumps(json_dict)
        json_fp.write(json_str)
    #results2json(image_filenames, results, prediction_output_path)
    print('Average inference time: {} ms'.format(1000.0* (inference_time / len(image_filenames))))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_path', type=str, default=None, help='Path to the model folder')
    parser.add_argument('-md', '--model_dir', type=str, default=None, help='Path to the model folder')
    parser.add_argument('-id', '--image_dir', type=str, default=None, help='Input image directory')
    parser.add_argument('-od', '--output_dir', type=str, default=None, help='Output directory')
    parser.add_argument('--confidence', type=float, default=0.9, help='')
    parser.add_argument('-vout', '--video_output', action='store_true', help='Use video as output format')
    parser.add_argument('--no-image', action='store_true', help='If set, the predicted images will not be saved.')
    parser.add_argument('--fps', type=int, default=6, help='FPS of output video')
    args = parser.parse_args()
    main(args)
