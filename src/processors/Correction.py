import os

import cv2
import numpy as np

from src.config import CONFIG_DEFAULTS as config
from src.logger import logger
from src.utils.imgutils import (
    ImageUtils,
    MainOperations,
)

from .interfaces.ImagePreprocessor import ImagePreprocessor


class Correction(ImagePreprocessor):
    def __init__(self, marker_ops, cwd):
        self.threshold_circles = []
        # img_utils = ImageUtils()

        # options with defaults
        self.marker_path = os.path.join(
            cwd, marker_ops.get("relativePath", "correction.jpg")
        )
        self.min_matching_threshold = marker_ops.get(
            "min_matching_threshold", 0.3)
        self.max_matching_variation = marker_ops.get(
            "max_matching_variation", 0.41)
        self.marker_rescale_range = marker_ops.get(
            "marker_rescale_range", (35, 100))
        self.marker_rescale_steps = marker_ops.get("marker_rescale_steps", 10)
        self.apply_erode_subtract = marker_ops.get("apply_erode_subtract", 1)
        if not os.path.exists(self.marker_path):
            logger.error(
                "Marker not found at path provided in template:",
                self.marker_path,
            )
            exit(31)

        marker = cv2.imread(self.marker_path, 0)

        marker = cv2.GaussianBlur(marker, (5, 5), 0)
        marker = cv2.normalize(
            marker, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX
        )

        if self.apply_erode_subtract:
            # TODO: verify its effectiveness in practical cases
            marker -= cv2.erode(marker, kernel=np.ones((5, 5)), iterations=5)

        self.marker = marker

    def __str__(self):
        return self.marker_path

    def exclude_files(self):
        return [self.marker_path]

    def apply_filter(self, image, args):
        threshold = 0.4
        imageG = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        w, h = self.marker.shape[::-1]
        res = cv2.matchTemplate(imageG, self.marker, cv2.TM_CCOEFF_NORMED)

        loc = np.where(res >= threshold)
        # print(loc)
        # cv2.imshow("found", res)
        # cv2.waitKey(0)
        mask = np.zeros_like(imageG)
        for pt in zip(*loc[::-1]):
            #a = cv2.rectangle(image, pt, (pt[0] + w, pt[1] + h), (0,0,255), 1)
            # Reduce the size of the rectangle by 3 pixels from each side
            cv2.rectangle(mask, (pt[0]+3, pt[1]+3),
                          (pt[0]+w-3, pt[1]+h-3), 255, -1)
            print(pt, "this is example")

        image = cv2.inpaint(image, mask, 2, cv2.INPAINT_NS)
        # return image

    # def crossMark():
    #     return np.array([[0,   0,   0,   0,   255, 255, 0,      0,   0,   0,    0,   0,   0],
    #                      [0,   0,   0,   0,   255, 255, 0,      0,   0,   0,    0,   0,   0],
    #                      [0,   0,   255, 255, 255, 255, 255,  255, 255, 255,    0,   0,   0],
    #                      [0,   0,   255, 255, 255, 255, 255,  255, 255, 255,    0,   0,   0],
    #                      [255, 255, 255, 255, 255, 255, 255,  255, 255, 255,    0,   0,   0],
    #                      [255, 255, 255, 255, 255, 255, 255,  255, 255, 255,    0,   0,   0],
    #                      [0,   255, 255, 255, 255, 255, 255,  255, 255, 255,    0,   0,   0],
    #                      [0,   0,   255, 255, 255, 255, 255,  255,   0,   0,    0,   0,   0],
    #                      [0,   0,   255, 255, 255, 255, 255,  255,   0,   0,    0,   0,   0],
    #                      [0,   0,   0,     0, 255, 255,   0,    0,   0,   0,    0,   0,   0],
    #                      [0,   0,   0,     0, 255, 255,   0,    0,   0,   0,    0,   0,   0],
    #                      [0,   0,   0,     0, 255, 255,   0,    0,   0,   0,    0,   0,   0]], dtype=np.uint8)
