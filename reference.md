---
jupyter:
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
  language_info:
    codemirror_mode:
      name: ipython
      version: 3
    file_extension: .py
    mimetype: text/x-python
    name: python
    nbconvert_exporter: python
    pygments_lexer: ipython3
    version: 3.10.13
  nbformat: 4
  nbformat_minor: 5
---

::: {#f26ec7d6-7f90-4af7-b350-cb58bf7aea68 .cell .markdown}
# Some part of this code was taken from here: <https://github.com/ultralytics/ultralytics/issues/4827> {#some-part-of-this-code-was-taken-from-here-httpsgithubcomultralyticsultralyticsissues4827}
:::

::: {#b5db56fa-504a-4bb9-95bd-b63e80a0c74b .cell .code execution_count="1"}
``` python
# !pip install tensorflow[and-cuda]
# !pip install opencv-python
# !pip install matplotlib
```
:::

::: {#f042a7d5-ae37-44b1-a6cc-5e892138d8bc .cell .code execution_count="2"}
``` python
import numpy as np
import cv2
import tensorflow as tf
from matplotlib import pyplot as plt
import glob
```

::: {.output .stream .stderr}
    2024-02-05 16:03:58.940709: I tensorflow/tsl/cuda/cudart_stub.cc:28] Could not find cuda drivers on your machine, GPU will not be used.
    2024-02-05 16:03:58.990594: I tensorflow/tsl/cuda/cudart_stub.cc:28] Could not find cuda drivers on your machine, GPU will not be used.
    2024-02-05 16:03:58.991463: I tensorflow/core/platform/cpu_feature_guard.cc:182] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
    To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
    2024-02-05 16:03:59.757977: W tensorflow/compiler/tf2tensorrt/utils/py_utils.cc:38] TF-TRT Warning: Could not find TensorRT
:::
:::

::: {#bef40239-c671-4c87-8005-5d7342c281ae .cell .code execution_count="3"}
``` python
confidence_threshold=0.5
iou_threshold=0.5
```
:::

::: {#00c7b1bc-d77f-462d-a8df-98a1a0106b0e .cell .code execution_count="4"}
``` python
CLASSES=['drone']
```
:::

::: {#bddc5d0b-7315-4de6-8b8f-06433e43556c .cell .code execution_count="5"}
``` python
IMG_FOLDER=glob.glob('./images/*')
MODEL_PATH="./best_float16.tflite"
```
:::

::: {#612ccaa2-fc99-49b3-88b4-bdf316c614eb .cell .code execution_count="6"}
``` python
def predict_and_show(model_path, img_names):
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    image_height = input_details[0]['shape'][1] 
    image_width = input_details[0]['shape'][2]

    for img_name in img_names:
        image=cv2.imread(img_name)
        
        resized_image= cv2.resize(image, (image_width, image_height))
        input_image = np.array(resized_image) #
        input_image = np.true_divide(input_image, 255, dtype=np.float32) 
        input_image = input_image[np.newaxis, :]
        
        interpreter.set_tensor(input_details[0]['index'], input_image)
        interpreter.invoke()

        output = interpreter.get_tensor(output_details[0]['index'])
        output = output[0]
        output = output.T

        boxes_xywh = output[..., :4] 
        scores = np.max(output[..., 4:], axis=1)
        classes = np.argmax(output[..., 4:], axis=1)

        indices = cv2.dnn.NMSBoxes(boxes_xywh, scores, confidence_threshold, iou_threshold)

        threshold = 0.25

        for i in indices:
            if scores[i] >= threshold:
                x_center, y_center, width, height = boxes_xywh[i]
                
                x1 = int((x_center - width / 2) * image_width)
                y1 = int((y_center - height / 2) * image_height)
                x2 = int((x_center + width / 2) * image_width)
                y2 = int((y_center + height / 2) * image_height)

                image_with_box = cv2.rectangle(resized_image, (x1,y1), (x2,y2), [0,0,255], 1)
                cv2.putText(image_with_box, f'{CLASSES[classes[i]]}:{scores[i]:.2f}',(x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
        
        
        try:
            plt.imshow(cv2.cvtColor(image_with_box, cv2.COLOR_BGR2RGB))
        except: 
            print('*** THE MODEL DID NOT DETECT A SINGLE OBJECT IN: ', img_name)
            plt.imshow(cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB))
        plt.show()

        
```
:::

::: {#8cba9c85-6063-4c30-9029-3ef3e1ab5589 .cell .code execution_count="7"}
``` python
predict_and_show(MODEL_PATH, IMG_FOLDER[:10])
```

::: {.output .stream .stderr}
    INFO: Created TensorFlow Lite XNNPACK delegate for CPU.
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/b6aa489555acfa0af3d800d069dd3240fa47fec3.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/00ec018e421529c6ad98b9bdd3d21b89267d3e45.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/2a42b6bd4469a9722a253bb63892691d0f0798b4.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/7e67d2e20800f3eff0feac3bd2a485250a78c4ec.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/131a9b0eb323a43bfc53ae51e5aa528607082ee5.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/725c20454ade56e595eb6decac24fe28cc14dfc7.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/76565f20754b38078091355d357f2361bfcd8106.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/7e69d00ec7de6b097e0529b7a23e0d6098ddedb4.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/f3a49bbc38a9950591e3713d44e574ffd4183a37.png)
:::

::: {.output .display_data}
![](vertopal_82c3af600fda4cec9cb590d978c95609/f3a49bbc38a9950591e3713d44e574ffd4183a37.png)
:::
:::
