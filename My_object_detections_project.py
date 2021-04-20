import numpy as np
import cv2 as cv
import os
import time
#branch test message 10：29 master

# from concurrent.futures import ThreadPoolExecutor,wait,ALL_COMPLETED,as_completed
yolo_dir = 'D:\Gao xiaojie Project\Object_detection\source'  # YOLO文件路径
weightsPath = os.path.join(yolo_dir, 'yolov3.weights')  # 权重文件
configPath = os.path.join(yolo_dir, 'yolov3.cfg')  # 配置文件
labelsPath = os.path.join(yolo_dir, 'coco.names')  # label名称
imgPath = os.path.join(yolo_dir, 'kite.jpg')  # 测试图像
videoPath = os.path.join(yolo_dir, 'cars.mp4')
CONFIDENCE = 0.5  # 过滤弱检测的最小概率
THRESHOLD = 0.4 # 非极大值抑制阈值
# 加载网络、配置权重
net = cv.dnn.readNetFromDarknet(configPath, weightsPath)  

#获取net中最后一层
def getOutputsNames(net):
    return net.getUnconnectedOutLayersNames()

#进行后处理
def postprocess(img, layerOutputs):
    (H, W) = img.shape[:2]
    # 过滤layerOutputs
    # layerOutputs的第1维的元素内容: [center_x, center_y, width, height, objectness, N-class score data]
    # 过滤后的结果放入：
    boxes = [] # 所有边界框（各层结果放一起）
    confidences = [] # 所有置信度
    classIDs = [] # 所有分类ID
    # # 1）过滤掉置信度低的框框
    for out in layerOutputs:  # 各个输出层
        for detection in out:  # 各个框框
            # 拿到置信度
            scores = detection[5:]  # 各个类别的置信度
            classID = np.argmax(scores)  # 最高置信度的id即为分类id
            confidence = scores[classID]  # 拿到置信度

            # 根据置信度筛查
            if confidence > CONFIDENCE:
                box = detection[0:4] * np.array([W, H, W, H])  # 框尺寸复原
                (centerX, centerY, width, height) = box.astype("int")
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)

    # # 2）应用非极大值抑制(non-maxima suppression，nms)进一步筛掉
    idxs = cv.dnn.NMSBoxes(boxes, confidences, CONFIDENCE, THRESHOLD) # boxes中，保留的box的索引index存入idxs
    # 得到labels列表
    with open(labelsPath, 'rt') as f:
        labels = f.read().rstrip('\n').split('\n')
    # 应用检测结果
    np.random.seed(42)
    COLORS = np.random.randint(0, 255, size=(len(labels), 3), dtype="uint8")  # 框框显示颜色，每一类有不同的颜色，每种颜色都是由RGB三个值组成的，所以size为(len(labels), 3)
    if len(idxs) > 0:
        for i in idxs.flatten():  # indxs是二维的，第0维是输出层，所以这里把它展平成1维
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])

            color = [int(c) for c in COLORS[classIDs[i]]]
            cv.rectangle(img, (x, y), (x+w, y+h), color, 2)  # 线条粗细为2px
            text = "{}: {:.4f}".format(labels[classIDs[i]], confidences[i])
            cv.putText(img, text, (x, y-5), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)  # cv.FONT_HERSHEY_SIMPLEX字体风格、0.5字体大小、粗细2px
        return img

#检测部分
def detect(img):
    blobImg = cv.dnn.blobFromImage(img, 1.0/255.0, (416, 416), None, True, False)# net需要的输入是blob格式的，用blobFromImage这个函数来转格式
    net.setInput(blobImg)  # # 调用setInput函数将图片送入输入层
    outInfo = getOutputsNames(net)
    layerOutputs = net.forward(outInfo)  # 得到各个输出层的、各个检测框等信息，是二维结构。
    img = postprocess(img,layerOutputs)
    return img

#主函数（图片）
def main_img():
    img = cv.imread(imgPath)
    img = detect(img)
    cv.imshow('detected image', img)
    cv.imwrite('detected_image.jpg',img)
    cv.waitKey(0)

#主函数（视频）
def main_video():
    img_lists=[]
    img_detect=[]
    cap =cv.VideoCapture(videoPath)
    w = int(cap.get(3))
    h = int(cap.get(4))
    fps = cap.get(cv.CAP_PROP_FPS)
    perimg_sec=int(float('%.2f' % (1/fps*1000)))
    fourcc = int(cap.get(cv.CAP_PROP_FOURCC))
    out = cv.VideoWriter('detect_result.mov',fourcc,fps,(w,h))
    while cap.isOpened():
        ret,img=cap.read()
        if img is not None:
            img_lists.append(img)
        else:
            break
    cap.release()

    # # 单线程(实时)
    # for img in img_lists:
    #     img = detect(img)
    #     img = cv.resize(img,None,fx=0.5,fy=0.5)
    #     cv.imshow('detected_video',img)
    #     if cv.waitKey(1) == 27:
    #         break
    # cv.destroyAllWindows()

    #单线程加速（缓存）
    for img in img_lists:
        try:
            img = detect(img)
            img_detect.append(img)
        except:
            break
    for img in img_detect:
        try:
            img = cv.resize(img,None,fx=0.5,fy=0.5)
            cv.imshow('detected video',img)
            if cv.waitKey(perimg_sec) == 27:
                break
        except:
            break
    cv.destroyAllWindows()

    #本地保存视频
    print('Start saving...')
    for img in img_detect:
        out.write(img)
    print('Save Finish')
    out.release()
    

    # #多线程加速(不支持多线程/多进程)
    # executor = ThreadPoolExecutor()
    # all_task = [executor.submit(detect,(img)) for img in img_lists ]
    # for future in as_completed(all_task):
    #     data=future.result()
    #     img = cv.resize(data,None,fx=0.5,fy=0.5)
    #     img_detect.append(img)
    # for img in img_detect:
    #     cv.imshow('detected video',img)
    #     #sleep时间越短，播放速度越快
    #     time.sleep(perimg_sec)
    #     if cv.waitKey(1) == 27:
    #         break
    # cv.destroyAllWindows()

#运行主函数
if __name__ == "__main__":
    main_img()
