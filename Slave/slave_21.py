from __future__ import print_function
import cv2 as cv
from multiprocessing.pool import ThreadPool
from collections import deque
from dbr import *
import time
from util import *

# Inicializar licencia de Dynamsoft Barcode Reader (DBR)
BarcodeReader.init_license("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

class ScanManager:
    MODE_AUTO_STITCH = 0
    MODE_MANUAL_STITCH = 1
    MODE_CAMERA_ONLY = 2

    def __init__(self):
        modes = (cv.Stitcher_PANORAMA, cv.Stitcher_SCANS)
        self.stitcher = cv.Stitcher.create(modes[1])
        self.stitcher.setPanoConfidenceThresh(0.1)
        self.panorama = []
        self.isPanoramaDone = False
        self.reader = BarcodeReader()

    def count_barcodes(self, frame):
        try:
            results = self.reader.decode_buffer(frame)
            return len(results)
        except BarcodeReaderError as e:
            print(e)
        
        return 0

    def save_frame(self, frame):
        filename = str(time.time()) + "_panorama.jpg"
        cv.imwrite(filename, frame)
        print("Saved to " + filename)

    def frame_overlay(self, frame):
        frame_cp = frame.copy()
        try:
            results = self.reader.decode_buffer(frame_cp)
            if results is not None:
                for result in results:
                    points = result.localization_result.localization_points
                    cv.line(frame_cp, points[0], points[1], (0, 255, 0), 2)
                    cv.line(frame_cp, points[1], points[2], (0, 255, 0), 2)
                    cv.line(frame_cp, points[2], points[3], (0, 255, 0), 2)
                    cv.line(frame_cp, points[3], points[0], (0, 255, 0), 2)
                    cv.putText(frame_cp, result.barcode_text, points[0], cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
                    
            return frame_cp
        except BarcodeReaderError as e:
            print(e)
            return None

    def stitch_frame(self, frame):
        try:
            results = self.reader.decode_buffer(frame)
            if results is not None:
                frame_cp = frame.copy()
                for result in results:
                    points = result.localization_result.localization_points
                    cv.line(frame_cp, points[0], points[1], (0, 255, 0), 2)
                    cv.line(frame_cp, points[1], points[2], (0, 255, 0), 2)
                    cv.line(frame_cp, points[2], points[3], (0, 255, 0), 2)
                    cv.line(frame_cp, points[3], points[0], (0, 255, 0), 2)
                    cv.putText(frame_cp, result.barcode_text, points[0], cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))

                if len(self.panorama) == 0:
                    self.panorama.append((frame, results, frame_cp))
                else:
                    preFrame = self.panorama[0][0]
                    preResults = self.panorama[0][1]
                    preFrameCp = self.panorama[0][2]

                    while len(results) > 0:
                        result = results.pop()
                        for preResult in preResults:
                            if preResult.barcode_text == result.barcode_text and preResult.barcode_format == result.barcode_format:
                                prePoints = preResult.localization_result.localization_points
                                points = result.localization_result.localization_points

                                preFrame = preFrame[0: preFrame.shape[0], 0: max(prePoints[0][0], prePoints[1][0], prePoints[2][0], prePoints[3][0]) + 10]
                                frame = frame[0: frame.shape[0], max(points[0][0], points[1][0], points[2][0], points[3][0]): frame.shape[1] + 10]

                                preFrameCp = preFrameCp[0: preFrameCp.shape[0], 0: max(prePoints[0][0], prePoints[1][0], prePoints[2][0], prePoints[3][0]) + 10]
                                frame_cp = frame_cp[0: frame_cp.shape[0], max(points[0][0], points[1][0], points[2][0], points[3][0]): frame_cp.shape[1] + 10]

                                frame = concat_images([preFrame, frame])
                                frame_cp = concat_images([preFrameCp, frame_cp])

                                results = self.reader.decode_buffer(frame)

                                self.panorama = [(frame, results, frame_cp)]
                                return frame, frame_cp

                return self.panorama[0][0], self.panorama[0][2]
                    
        except BarcodeReaderError as e:
            print(e)
            return None, None

        return None, None


    def process_frame(self, frame):
        results = None
        try:
            results = self.reader.decode_buffer(frame)
        except BarcodeReaderError as bre:
            print(bre)
        
        return results

    def clean_deque(self, tasks):
        while len(tasks) > 0:
            tasks.popleft()

    def close_window(self, window_name):
        try:
            cv.destroyWindow(window_name)
        except:
            pass

    def run(self):
        import sys
        try:
            fn = sys.argv[1]
        except:
            fn = 0
        cap = cv.VideoCapture(fn)

        threadn = 1
        barcodePool = ThreadPool(processes=threadn)
        panoramaPool = ThreadPool(processes=threadn)
        cameraTasks = deque()
        panoramaTask = deque()
        mode = self.MODE_CAMERA_ONLY
        image = None
        imageCp = None
        panoramaImage = None
        panoramaImageCp = None

        while True:
            ret, frame = cap.read()
            frame_cp = frame.copy()
            cv.putText(frame, 'A: auto pano, M: manual pano, C: capture, O: camera, S: stop', (10, 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
            cv.putText(frame, 'Barcode & QR Code Scanning ...', (10, 50), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

            while len(cameraTasks) > 0 and cameraTasks[0].ready():
                results = cameraTasks.popleft().get()
                if results is not None:
                    for result in results:
                        points = result.localization_result.localization_points
                        cv.line(frame, points[0], points[1], (0, 255, 0), 2)
                        cv.line(frame, points[1], points[2], (0, 255, 0), 2)
                        cv.line(frame, points[2], points[3], (0, 255, 0), 2)
                        cv.line(frame, points[3], points[0], (0, 255, 0), 2)
                        cv.putText(frame, result.barcode_text, points[0], cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
                
            if len(cameraTasks) < threadn:
                task = barcodePool.apply_async(self.process_frame, (frame_cp,))
                cameraTasks.append(task)

            if mode == self.MODE_MANUAL_STITCH:
                cv.putText(frame, 'Manual Panorama ...', (10, 70), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))
            elif mode == self.MODE_AUTO_STITCH:
                cv.putText(frame, 'Auto Panorama ...', (10, 70), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))
                if not self.isPanoramaDone and len(panoramaTask) < threadn:
                    task = panoramaPool.apply_async(self.stitch_frame, (frame_cp,))
                    panoramaTask.append(task)

            if mode == self.MODE_MANUAL_STITCH or mode == self.MODE_AUTO_STITCH:
                while len(panoramaTask) > 0 and panoramaTask[0].ready():
                    image, imageCp = panoramaTask.popleft().get()
                    if image is not None:
                        panoramaImage = image.copy()
                        panoramaImageCp = imageCp.copy()
                        cv.imshow('panorama', panoramaImageCp)
            
            ch = cv.waitKey(1)
            if ch == ord('q'):
                break
            elif ch == ord('o'):
                mode = self.MODE_CAMERA_ONLY
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('a'):
                mode = self.MODE_AUTO_STITCH
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('m'):
                mode = self.MODE_MANUAL_STITCH
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('c'):
                self.isPanoramaDone = True
                if mode == self.MODE_MANUAL_STITCH or mode == self.MODE_AUTO_STITCH:
                    self.save_frame(panoramaImage)
            elif ch == ord('s'):
                self.isPanoramaDone = False
                self.close_window('panorama')

            cv.imshow('camera', frame)

        cap.release()
        cv.destroyAllWindows()

if __name__ == '__main__':
    scan = ScanManager()
    scan.run()
