import os

import cv2
import numpy as np

from src.config import CONFIG_DEFAULTS as config
from src.logger import logger
from src.utils.imgutils import (
    ImageUtils,
    MainOperations,
    four_point_transform,
    normalize_util,
)

from .interfaces.ImagePreprocessor import ImagePreprocessor


class CropOnMarkers(ImagePreprocessor):
    def __init__(self, marker_ops, cwd):
        self.threshold_circles = []
        # img_utils = ImageUtils()

        # options with defaults
        self.marker_path = os.path.join(
            cwd, marker_ops.get("relativePath", "omr_marker.jpg")
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

        marker = cv2.imread(self.marker_path, 1)

        if "sheetToMarkerWidthRatio" in marker_ops:
            # TODO: processing_width should come through proper channel
            marker = ImageUtils.resize_util(
                marker,
                config.dimensions.processing_width
                / int(marker_ops["sheetToMarkerWidthRatio"]),
            )
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

    # Resizing the marker within scaleRange at rate of descent_per_step to
    # find the best match.
    def getBestMatch(self, image_eroded_sub):

        descent_per_step = (
            self.marker_rescale_range[1] - self.marker_rescale_range[0]
        ) // self.marker_rescale_steps
        _h, _w = self.marker.shape[:2]
        res, best_scale = None, None
        all_max_t = 0

        for r0 in np.arange(
            self.marker_rescale_range[1],
            self.marker_rescale_range[0],
            -1 * descent_per_step,
        ):  # reverse order
            s = float(r0 * 1 / 100)
            if s == 0.0:
                continue
            rescaled_marker = ImageUtils.resize_util_h(
                self.marker, u_height=int(_h * s)
            )
            # res is the black image with white dots
            res = cv2.matchTemplate(
                image_eroded_sub, rescaled_marker, cv2.TM_CCOEFF_NORMED
            )

            max_t = res.max()
            if all_max_t < max_t:
                # print('Scale: '+str(s)+', Circle Match: '+str(round(max_t*100,2))+'%')
                best_scale, all_max_t = s, max_t

        if all_max_t < self.min_matching_threshold:
            logger.warning(
                "\tTemplate matching too low! Consider rechecking preProcessors applied before this."
            )
            if config.outputs.show_image_level >= 1:
                show("res", res, 1, 0)

        if best_scale is None:
            logger.warning(
                "No matchings for given scaleRange:", self.marker_rescale_range
            )
        return best_scale, all_max_t

    def apply_filter(self, image, args):
        image_eroded_sub = normalize_util(
            image
            if self.apply_erode_subtract
            else (image - cv2.erode(image, kernel=np.ones((5, 5)), iterations=5))
        )
        # Quads on warped image
        quads = {}
        h1, w1 = image_eroded_sub.shape[:2]
        midh, midw = h1 // 3, w1 // 2
        origins = [[0, 0], [midw, 0], [0, midh], [midw, midh]]
        quads[0] = image_eroded_sub[0:midh, 0:midw]
        quads[1] = image_eroded_sub[0:midh, midw:w1]
        quads[2] = image_eroded_sub[midh:h1, 0:midw]
        quads[3] = image_eroded_sub[midh:h1, midw:w1]

        # Draw Quadlines
        image_eroded_sub[:, midw: midw + 2] = 255
        image_eroded_sub[midh: midh + 2, :] = 255

        best_scale, all_max_t = self.getBestMatch(image_eroded_sub)
        if best_scale is None:
            # TODO: Plot and see performance of marker_rescale_range
            if config.outputs.show_image_level >= 1:
                MainOperations.show("Quads", image_eroded_sub)
            return None

        optimal_marker = ImageUtils.resize_util_h(
            self.marker, u_height=int(self.marker.shape[0] * best_scale)
        )
        _h, w = optimal_marker.shape[:2]
        centres = []
        sum_t, max_t = 0, 0
        logger.info("Matching Marker:\t", end=" ")
        for k in range(0, 4):
            res = cv2.matchTemplate(
                quads[k], optimal_marker, cv2.TM_CCOEFF_NORMED)
            max_t = res.max()
            logger.info(
                f"Quarter{str(k + 1)}: {str(round(max_t, 3))} ", end="\t")
            if (
                max_t < self.min_matching_threshold
                or abs(all_max_t - max_t) >= self.max_matching_variation
            ):
                # Warning - code will stop in the middle. Keep Threshold low to
                # avoid.
                logger.error(
                    args["current_file"].name,
                    "\nError: No circle found in Quad",
                    k + 1,
                    "\n\t min_matching_threshold",
                    self.min_matching_threshold,
                    "\t max_matching_variation",
                    self.max_matching_variation,
                    "\t max_t",
                    max_t,
                    "\t all_max_t",
                    all_max_t,
                )
                if config.outputs.show_image_level >= 1:
                    MainOperations.show(
                        "no_pts_" +
                        args["current_file"].name, image_eroded_sub, 0
                    )
                    MainOperations.show(
                        "res_Q" + str(k + 1) + " (" + str(max_t) + ")", res, 1
                    )
                return None

            pt = np.argwhere(res == max_t)[0]
            pt = [pt[1], pt[0]]
            pt[0] += origins[k][0]
            pt[1] += origins[k][1]
            # print(">>",pt)
            image = cv2.rectangle(
                image, tuple(pt), (pt[0] + w, pt[1] + _h), (150, 150, 150), 2
            )
            # display:
            image_eroded_sub = cv2.rectangle(
                image_eroded_sub,
                tuple(pt),
                (pt[0] + w, pt[1] + _h),
                (50, 50, 50) if self.apply_erode_subtract else (155, 155, 155),
                4,
            )
            centres.append([pt[0] + w / 2, pt[1] + _h / 2])
            sum_t += max_t
        logger.info("Optimal Scale:", best_scale)
        # analysis data
        self.threshold_circles.append(sum_t / 4)

        image = four_point_transform(image, np.array(centres))
        # appendSaveImg(1,image_eroded_sub)
        # appendSaveImg(1,image_norm)

        ImageUtils.append_save_img(2, image_eroded_sub)
        # Debugging image -
        # res = cv2.matchTemplate(image_eroded_sub,optimal_marker,cv2.TM_CCOEFF_NORMED)
        # res[ : , midw:midw+2] = 255
        # res[ midh:midh+2, : ] = 255
        # show("Markers Matching",res)
        if config.outputs.show_image_level >= 2 and config.outputs.show_image_level < 4:
            image_eroded_sub = ImageUtils.resize_util_h(
                image_eroded_sub, image.shape[0]
            )
            image_eroded_sub[:, -5:] = 0
            h_stack = np.hstack((image_eroded_sub, image))
            MainOperations.show(
                "Warped: " + args["current_file"].name,
                ImageUtils.resize_util(
                    h_stack, int(config.dimensions.display_width * 1.6)
                ),
                0,
                0,
                [0, 0],
            )
        # iterations : Tuned to 2.
        # image_eroded_sub = image_norm - cv2.erode(image_norm, kernel=np.ones((5,5)),iterations=2)
        return image
