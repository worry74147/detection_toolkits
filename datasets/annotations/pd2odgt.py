import json
from tqdm import tqdm
import os


''''
{
    "ID": "273271,c9db000d5146c15", 
    "gtboxes": 
    [
        {"fbox": [72, 202, 163, 503], 
          "tag": "person", 
          "hbox": [171, 208, 62, 83], 
          "extra": {
              "box_id": 0, 
              "occ": 0},
          "vbox": [72, 202, 163, 398], 
          "head_attr": {
              "ignore": 0, 
              "occ": 0, 
              "unsure": 0}
        }, ....]
}
{
    second..
}
'''


'''
{
    'image id' : 1
    'image size' :{'height': 15052, 'width': 26753}
    'objects list':[
        {
            'category' : 'fake person',
            'rect': {
                'tl':{
                    'x': 0.63662617515, 'y': 0.37321539885
                },
                'br':{
                    'x': 0.6400970751, 'y': 0.3852374918
                }
            }
        },
        {
            'category' : 'person', 
            'pose': 'walking',
            'riding type': 'null',
            'age': 'adult',
            'rect': {
                'head': {'tl': {'x': 0.639550533025, 'y': 0.37646010757500004}, 'br': {'x': 0.642353550675, 'y': 0.382941285325}},
                'visible body': {'tl': {'x': 0.6348781676999999, 'y': 0.376453035725}, 'br': {'x': 0.645220085775, 'y': 0.417943317325}},
                'full body': {'tl': {'x': 0.63485517, 'y': 0.37643610225}, 'br': {'x': 0.645241075725, 'y': 0.41934146520000004}}
                }
        }
        

    ]
}

'''

def pdbox_toxywh(pdbox,W,H):
    tl_x = int(pdbox['tl']['x']*W)
    tl_y = int(pdbox['tl']['y']*H)
    br_x = int(pdbox['br']['x']*W)
    br_y = int(pdbox['br']['y']*H)
    return [tl_x,tl_y,br_x-tl_x,br_y-tl_y]

def main(args):
    with open(args.panda_json_file,'r') as reader:
        pt = json.loads(reader.read())

    tq_pt = tqdm(pt.items())
    A = set([])
    records = []
    for key,record in tq_pt:
        box_id = 0
        gtboxes = []
        
        H = record['image size']['height']
        W = record['image size']['width']

        for i,obj in enumerate(record['objects list']):
            tq_pt.set_description('[-] Processing {}[{}/{}]'.format(key.split('.')[0],i,len(record['objects list'])))
            tq_pt.refresh()
            #print(obj['category'])
            A.add(obj['category'])
            if obj['category'] == 'person': # has vbox fbox head
                #print(obj)
                rect = obj['rects']
                
                gtbox = {
                    "fbox": pdbox_toxywh(rect['full body'],W,H), 
                    "tag": "person", 
                    "hbox": pdbox_toxywh(rect['head'],W,H), 
                    "extra": { "box_id": box_id, "occ": 0},
                    "vbox": pdbox_toxywh(rect['visible body'],W,H), 
                    "head_attr": {
                        "ignore": 0, 
                        "occ": 0, 
                        "unsure": 0}
                }
                box_id += 1
            elif obj['category'] == 'ignore': # Nah.. only one box
                rect = obj['rect']
                #print(obj)
                #exit()
                box = pdbox_toxywh(rect,W,H)
                gtbox = {
                    "fbox": box, 
                    "tag": "mask", 
                    "hbox": box, 
                    "extra": {"ignore": 1},
                    "vbox":box, 
                    "head_attr": {}
                }
            else: # NAAaaaah => crowd,people,fake person
                continue
            gtboxes.append(gtbox)
        records.append({
                            "ID": key.split('.')[0], 
                            "gtboxes": gtboxes
                        })
        #exit()
    os.makedirs(args.output_dir,exist_ok=True)
    tq_re = tqdm(records)
    tq_re.set_description('[-]Since it is not just a list...')
    with open(args.output_dir + '/pj.odgt', 'w') as f:
        for r in tq_re:
            f.writelines(str(r).replace('\'','\"')+'\n')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-pt', '--panda_json_file', type=str, default=None)
    parser.add_argument('-od', '--output_dir', type=str, default=None)
    args = parser.parse_args()
    main(args)