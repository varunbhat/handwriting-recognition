import os
import re
from numpy import random
from queue import Queue
from threading import Thread

import cv2
import math
import numpy as np
import matplotlib.pyplot as plot
import sys

# os.environ['THEANO_FLAGS'] = "device=cpu1"
os.environ['OMP_NUM_THREADS'] = "5"
import theano

theano.config.floatX = 'float32'

from keras.layers.convolutional import Convolution2D
from keras.layers.core import Dropout, Flatten, Dense
from keras.layers.pooling import MaxPooling2D
from keras.models import Sequential

image_path = 'iamDB/data/forms1'

thread_queue = Queue(10)

ascii_fp = open('/home/varunbhat/workspace/ml_project/iamDB/data/ascii/words.txt')
word_data = ascii_fp.read()
ascii_fp.close()


class HandwritingRecognition:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image_id = image_path.split('/')[-1].split('.')[-2]
        self.image = None
        self.debug = False
        self.image = None
        self.y_offset = (620, 2800)
        self.x_offset = (0, -1)
        self.segments = []
        self.dataset_segments = []
        self.dataset_labels = []

    def segment(self):
        self.read_image(self.image_path) if self.image is None else 1
        self.y_offset = (620, 2800)
        self.x_offset = (0, self.image.shape[1])
        temp_image = np.copy(self.image)
        temp_image = temp_image[self.y_offset[0]:self.y_offset[1], self.x_offset[0]:self.x_offset[1]]
        temp_image = cv2.blur(temp_image, (30, 30))
        temp_image = self.normalize(temp_image)
        # self.show_image(cv2.resize(temp_image, (0, 0), fx=0.3, fy=0.3))
        y_segments = self.segment_lines(temp_image)
        x_segments = []
        for s, e in y_segments:
            temp_image_cropped = np.copy(self.image[s:e, :])
            temp_image_cropped = cv2.blur(temp_image_cropped, (50, 200))
            temp_image_cropped = self.normalize(temp_image_cropped)
            x_segments.append(self.segment_words(temp_image_cropped))

        self.segments = []
        for line in range(len(x_segments)):
            self.segments.append([(y_segments[line], (x_s, x_e)) for x_s, x_e in x_segments[line]])

    def normalize(self, image=None):
        t_image = image[:] if image is not None else self.image[:]
        hist = cv2.calcHist([t_image], [0], None, [256], [0, 256]).T[0]
        threshold_val = 0

        # fig, plt = plot.subplots(1, 1)
        # # plt.set_ylim(, 2)
        # plt.set_xlim(150, 255)
        # plt.plot(range(len(hist)), hist)
        # plot.show()

        for i in range(len(hist)):
            if hist[i] > max(hist) * 0.02234:
                threshold_val = i
                break

        # threshold_val = 200
        # print(threshold_val, threshold_val + ((255 - threshold_val) * .75))
        cv2.threshold(t_image, threshold_val, threshold_val + ((255 - threshold_val) * .40), cv2.THRESH_OTSU, t_image)
        cv2.normalize(t_image, t_image, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        # self.show_image(cv2.resize(t_image, (0, 0), fx=0.3, fy=0.3) * 255)
        return t_image

    def segment_lines(self, image=None):
        start_image = image if image is not None else self.image
        t_image = start_image

        #  Get the histogram of the data
        data = (np.dot(t_image, np.ones(t_image.shape[1])) / t_image.shape[1]) < 0.95
        # data1 = (np.dot(t_image, np.ones(t_image.shape[1])) / t_image.shape[1])

        # fig, plt = plot.subplots(1, 1)
        # plt.set_ylim(-1, 2)
        # plt.set_xlim(0, t_image.shape[1])
        # plt.plot(range(len(data)), data)
        # plot.show()

        start = 0
        segment = []

        for i in range(1, t_image.shape[0]):
            if data[i - 1] == 0 and data[i] == 1:
                start = i
            elif data[i - 1] == 1 and data[i] == 0:
                _s, _e = (start + self.y_offset[0], i + self.y_offset[0])
                if _e - _s < 5:
                    continue
                segment.append((start + self.y_offset[0], i + self.y_offset[0]))
                # self.show_image(cv2.resize(self.image[_s:_e, :], (0, 0), fx=0.3, fy=0.3))
        return segment

    def segment_words(self, image):
        start_image = image if image is not None else self.image
        t_image = start_image

        # self.show_image(t_image * 255)
        # print(t_image.shape[0])
        #  Get the histogram of the data
        # if t_image.shape[0] < 10 or t_image.shape[1] < 10:
        #     return []
        data = (np.dot(t_image.T, np.ones(t_image.shape[0])) / t_image.shape[0]) < 0.95
        start = 0
        segment = []

        for i in range(1, t_image.shape[1]):
            if data[i - 1] == 0 and data[i] == 1:
                start = i
            elif data[i - 1] == 1 and data[i] == 0:
                _s, _e = (start + self.x_offset[0], i + self.x_offset[0])
                if _e - _s < 5:
                    continue
                segment.append((start + self.x_offset[0], i + self.x_offset[0]))
        return segment

    def read_image(self, img_path, bw=True):
        if bw:
            self.image = cv2.imread(img_path, 0)
        else:
            self.image = cv2.imread(img_path)

    def show_image(self, image=None, window='image'):
        # show the image specified in the window
        cv2.imshow(window, image if image is not None else self.image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def show_segmented_words(self):
        for line in self.segments:
            for ((y_s, y_e), (x_s, x_e)) in line:
                self.show_image(self.image[y_s:y_e, x_s:x_e])

    def get_segmented_image_array(self, segments):
        arr = []
        for line in segments:
            for ((y_s, y_e), (x_s, x_e)) in line:
                arr.append(self.image[y_s - 6:y_e + 6, x_s + 3:x_e + 3])
        return arr

    def get_segmented_dataset_images(self):
        return self.get_segmented_image_array(self.dataset_segments)

    def get_segmented_images(self):
        return self.get_segmented_image_array(self.segments)

    def read_dataset_segmentation(self, word_dataset):
        self.read_image(self.image_path) if self.image is None else 1
        rows = re.findall('(%s-.*)' % self.image_id, word_dataset)
        rexp = re.compile(
            '(?P<id>[a-z0-9\-]+) (?P<status>err|ok) (?P<threshold>\d+) (?P<coordinates>([\d\-]+ ){4})'
            '(?P<typeset>.*?) (?P<word>.*)')

        dataset = []
        labels = []
        for data in rows:
            res = rexp.match(data)
            if res is None:
                continue
            if res.group('status') == 'ok':
                x, y, w, h = (int(_i) for _i in res.group('coordinates').split(' ')[:4])
                dataset.append(((y, y + h), (x, x + h)))
                labels.append(res.group('word'))
                # self.show_image(self.image[y:y + h, x:x + w])
            else:
                continue
        self.dataset_segments.append(dataset)
        self.dataset_labels.append(labels)

    def get_dataset_segmentation(self):
        return self.dataset_labels, self.dataset_segments

    def get_dataset_labels(self):
        return self.dataset_labels

    @classmethod
    def show(clf, image, window='image'):
        cv2.imshow(window, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


class ConvNet:
    def __init__(self):
        self.model = Sequential()
        self.model.add(Convolution2D(30, 5, 5, border_mode='valid', input_shape=(1, 128, 128), activation='relu'))
        self.model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
        self.model.add(Convolution2D(15, 3, 3, activation='relu'))
        self.model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
        self.model.add(Convolution2D(10, 2, 2, activation='relu'))
        self.model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
        self.model.add(Dropout(0.5))
        self.model.add(Flatten())
        self.model.add(Dense(128, activation='relu'))
        self.model.add(Dense(50, activation='relu'))
        self.model.add(Dense(80, activation='softmax'))
        self.model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
        self.training_image_refs = []
        self.training_labels = []
        self.test_image_refs = []
        self.test_labels = []

    def set_training(self, tset):
        self.training_image_refs = []
        self.training_labels = []
        for hclass in tset:
            self.training_labels.append(hclass.get_dataset_labels())
            self.training_image_refs.append(hclass.get_segmented_dataset_images())

    def set_validation(self, vset):
        self.test_image_refs = []
        self.test_labels = []
        for hclass in vset:
            self.test_labels.append(hclass.get_dataset_labels())
            self.test_image_refs.append(hclass.get_segmented_dataset_images())

    def format_images(self):
        for ds in [self.training_image_refs, self.test_image_refs]:
            for j, form_imgs in enumerate(ds):
                for i, img in enumerate(form_imgs):
                    if 0 in img.shape:
                        form_imgs[i] = None
                        continue
                    ar = (int(28 * img.shape[1] / img.shape[0]), 28) if img.shape[0] < 28 is not 0 else (28, 28)
                    form_imgs[i] = cv2.resize(img, ar)
                    print(self.training_labels)
                    HandwritingRecognition.show(img)
        print(self.training_image_refs)


def segment(pth):
    hreco = HandwritingRecognition(os.path.join(image_path, pth))
    hreco.segment()
    hreco.show_segmented_words()
    # count = 1
    # for img in hreco.get_segmented_image_array():
    #     if not os.path.exists(os.path.join('segmented', pth)):
    #         os.mkdir(os.path.join('segmented', pth))
    #     cv2.imwrite(os.path.join('segmented', pth, '%d.png' % count), img)
    #     count += 1


def read_dataset(path):
    global word_data
    hreco = HandwritingRecognition(os.path.join(image_path, path))
    hreco.read_dataset_segmentation(word_data)
    return hreco


def dispacher():
    while True:
        t = thread_queue.get()
        t.start()


# if __name__ == '__main__':
#     # Thread(target=dispacher).start()
#     dataset = []
#     for pth in os.listdir(image_path):
#         if 'png' not in pth:
#             continue
#         # print(pth)
#         dataset.append(read_dataset(pth))
#         # thread_queue.put(Thread(target=segment, args=(pth,)))
#         segment(pth)

if __name__ == '__main__':
    dataset = []
    for pth in os.listdir(image_path):
        if 'png' not in pth:
            continue
        dataset.append(read_dataset(pth))
        print("Reading:", pth)

    random.shuffle(dataset)
    cnn = ConvNet()
    cnn.set_training(dataset[:int(len(dataset) * .8)])
    cnn.set_validation(dataset[int(len(dataset) * .8):])
    cnn.format_images()
