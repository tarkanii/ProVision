import math, time
import pymeanshift as pms
import numpy as np
import cv2


DIR_HORIZONTAL = 0
DIR_VERTICAL = 1


def find_edges(img, img_labels):
    res = np.copy(img)

    for row in range(1, img_labels.shape[0]):
        for col in range(1, img_labels.shape[1]):
            if (img_labels[row, col] != img_labels[row - 1, col]
             or img_labels[row, col] != img_labels[row, col - 1]):
                res[row, col] = (0, 0, 255)

    return res


class ForegroundObject:

    def __init__(self, center, label):
        self.c_row, self.c_col = center
        self.main_label = label
        self.labels = [label]
        self.boundaries = []


class Detector:

    def __init__(self, original_img, segmented_img, img_labels):
        self.original_img = original_img
        self.img_labels = img_labels
        self.f_object = Detector.undefined

        img_hsv = cv2.cvtColor(segmented_img, cv2.COLOR_BGR2HSV)

        # Normalize color properties
        #   hue:         [0; 2pi]
        #   saturation:  [0: 100]
        #   vibration:   [0; 100]
        self.hue = np.float32(img_hsv[:, :, 0] * 2 * math.pi / 180)         # Convert degrees to radians
        self.sat = np.float32(img_hsv[:, :, 1] / 255)
        self.val = np.float32(img_hsv[:, :, 2] / 255)

    def __setattr__(self, key, value):
        if key == 'f_object':
            if isinstance(value, ForegroundObject) or isinstance(value, property):
                self.__dict__[key] = value
            else:
                raise ValueError("set_foreground_object method " +
                                 "should take instance of ForegroundObject class as parameter")
        else:
            self.__dict__[key] = value

    def find_cluster_boundaries(self, img, label):
        rows, cols = np.where(self.img_labels == label)
        boundaries = list()

        for row in set(rows):
            col_list = cols[np.where(rows == row)]
            left, right = np.min(col_list), np.max(col_list)

            img[row, left] = (0, 0, 255)
            img[row, right] = (0, 0, 255)

            boundaries.append((row, left))
            boundaries.append((row, right))

        boundaries[:2] = []
        boundaries[-2:] = []

        top_bound, bottom_bound = np.min(rows), np.max(rows)

        top_index = np.where(rows == top_bound)
        bottom_index = np.where(rows == bottom_bound)

        for index in top_index[0]:
            boundaries.insert(0, (rows[index], cols[index]))
        for index in bottom_index[0]:
            boundaries.append((rows[index], cols[index]))

        img[rows[top_index], cols[top_index]] = (0, 0, 255)
        img[rows[bottom_index], cols[bottom_index]] = (0, 0, 255)

        return boundaries

    def compute_avg(self):

        numerator_hue = numerator_sat = numerator_val = denominator = 0
        for label in self.f_object.labels:
            index = np.where(self.img_labels == label)

            numerator_hue += np.sum(self.hue[index])
            numerator_sat += np.sum(self.sat[index])
            numerator_val += np.sum(self.val[index])

            denominator += len(index[0])

        avg_hue = numerator_hue / denominator
        avg_sat = numerator_sat / denominator
        avg_val = numerator_val / denominator

        return self.find_color_distance(
            (avg_hue, avg_sat, avg_val),
            (
                self.hue[self.f_object.c_row, self.f_object.c_col],
                self.sat[self.f_object.c_row, self.f_object.c_col],
                self.val[self.f_object.c_row, self.f_object.c_col],
            )
        )

    def detect_object(self):
        start = time.time()

        img = np.copy(self.original_img)

        self.f_object.boundaries = self.find_cluster_boundaries(img, self.f_object.main_label)

        neighbour = set()
        for row, col in self.f_object.boundaries:
            if self.img_labels[row, col - 1] not in self.f_object.labels: neighbour.add(self.img_labels[row, col - 1])
            if self.img_labels[row, col + 1] not in self.f_object.labels: neighbour.add(self.img_labels[row, col + 1])
            if self.img_labels[row - 1, col] not in self.f_object.labels: neighbour.add(self.img_labels[row - 1, col])
            if self.img_labels[row + 1, col] not in self.f_object.labels: neighbour.add(self.img_labels[row + 1, col])

        print((
                self.hue[self.f_object.c_row, self.f_object.c_col],
                self.sat[self.f_object.c_row, self.f_object.c_col],
                self.val[self.f_object.c_row, self.f_object.c_col],
            ))

        winner = []
        for label in neighbour:
            self.f_object.labels = [self.f_object.main_label, label]
            if self.compute_avg() < 0.12:
                self.img_labels[np.where(self.img_labels == label)] = self.f_object.main_label

        img[np.where(self.img_labels != self.f_object.main_label)] = 0

        print(time.time() - start)

        return img

    def find_color_distance(self, p1, p2):
        h1, s1, v1 = p1
        h2, s2, v2 = p2

        if h1 == h2 and s1 == s2 and v1 == v2: return 0

        return math.sqrt(
            s1 ** 2 + s2 ** 2 -
            s1 * s2 * math.cos(min(abs(h1 - h2), math.pi * 2 - abs(h1 - h2))) * 2 +
            (v1 - v2) ** 2
        )

    @staticmethod
    def get_undefined_object(self):
        raise KeyError("You have to define instance of ForegroundObject with set_foreground_object method")

    undefined = property(get_undefined_object)









