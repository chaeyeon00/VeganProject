import xml.dom.minidom
import os
import io
import re

# 이미지 처리
import cv2
import numpy as np

from google.cloud import vision

import pandas as pd
import requests


def vegn_main(imgFile):
    #path = 'asset/images/test02_1.jpeg'
    # 이미지 전처리 호출
    print("vegn_main 호출")
    trimCnt= trimImage("media/"+imgFile)
    # ocr 정보 가져오기

    if trimCnt is not False:
        ocr_dict = getImageOCR(trimCnt, "media/"+imgFile)

        if ocr_dict != {}:
            # 상품명, 원재료 정보
            prdName, rawmtrlAllList = getPrdInfo(ocr_dict)
            # 최종 호출 및 OUTPUT
            typeList, metrialClassList = getVeganStep(rawmtrlAllList)

            conetxt = changeType(typeList, metrialClassList)


            return conetxt
    # ocr결과가 없는 경우
    return False


def googleConfig():
    """
        Google Cloud vision API 연결을 위한 환경 설정
        Parameters : None
        - Google로부터 발급받은 json 파일을 이용하여 API 연결
    """
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'images/config/service-account-file.json'

    client_options = {'api_endpoint': 'eu-vision.googleapis.com'}
    client = vision.ImageAnnotatorClient(client_options=client_options)
    return client


# google OCR 호출
def googleOCR(path):
    """
        Google Cloud vision API를 호출하여 Text 추출
        Parameters :
            path : 이미지 파일이 위치한 경로 및 파일명
        - Google Cloud vision API의 OCR 호출 결과를 가져옴
    """

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    # 구글 API 호출
    image = vision.Image(content=content)
    client = googleConfig()
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts


# 20개의 이미지 OCR
def getImageOCR(trimCnt, img):
    """
        Google Cloud vision API 호출 및 이미지별 text 추출
        Parameters :
        - 원본 이미지에서 라인 기준으로 추출된 20개의 이미지에 대해서 OCR 호출
        Return : ocr_dict ["이미지 파일명", "ocr의 text"]
    """
    ocr_dict = {}
    check = False
    for i in range(0, trimCnt):
        imgFile = 'images/TestImage/test_trim' + str(i) + '.jpg'
        texts = googleOCR(imgFile)
        ocr_text = ""

        if texts != []:
            ocr_text = texts[0].description
            if "원재료" in ocr_text :
                check = True

        ocr_dict["test_trim" + str(i) + ".jpg"] = ocr_text

    if check is False :
        texts = googleOCR(img)
        if texts != []:
            ocr_text = texts[0].description
            ocr_dict["test_trim0.jpg"] = ocr_text

    return ocr_dict

# 원본 이미지에서 "표" 추출 하고 20개의  영역으로 나누어서 저장하기
def trimImage(imgPath):
    """
        원본 이미지(imgPath)로부터 '라인'을 추출 하고 20개의 사격형으로 나누어 저장
        Parameters : imgPath  = 이미지 파일명
        - 원본 이미지에서 라인 기준으로 추출된 20개의 이미지에 대해서 OCR 호출
    """
    # 표 추출하기
    # 이미지 불러오기
    img = cv2.imread(imgPath)

    # 이미지 이진화 처리
    gray_scale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th1, img_bin = cv2.threshold(gray_scale, 150, 225, cv2.THRESH_BINARY)
    img_bin = ~img_bin

    # 연산적용
    ### selecting min size as 15 pixels
    line_min_width = 10
    kernal_h = np.ones((1, line_min_width), np.uint8)
    kernal_v = np.ones((line_min_width, 1), np.uint8)

    # h(수평 - 가로), v(수직 - 세로)
    img_bin_h = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernal_h)
    img_bin_v = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernal_v)
    img_bin_final = img_bin_h | img_bin_v

    final_kernel = np.ones((3, 3), np.uint8)
    img_bin_final = cv2.dilate(img_bin_final, final_kernel, iterations=1)

    retval, labels, stats, centroids = cv2.connectedComponentsWithStats(~img_bin_final, connectivity=8, ltype=cv2.CV_32S)
    # stats :  N행 5열  x, y, width, height, area
    # numpy to pandas && area순으로 정렬
    try:

        statsDf = pd.DataFrame(stats[2:])
        statsDf = statsDf.sort_values(4, ascending=False)  # for statsDf.iterrows():
        print(statsDf.size)
        trimCnt = 20 if statsDf.size > 20 else statsDf.size
        # 상위 20개의 이미지 그룹핑하여 해당 데이터 set저장
        for i in range(0, trimCnt):
            x = statsDf.iloc[i][0]
            y = statsDf.iloc[i][1]
            w = statsDf.iloc[i][2]
            h = statsDf.iloc[i][3]

            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            testImg = 'images/TestImage/test_trim' + str(i) + '.jpg'  # 경로 변경 필요

            img_trim = img[y:y + h, x:]
            cv2.imwrite(testImg, img_trim)
            org_image = cv2.imread(testImg)
    except :
        return False

    return trimCnt


# 제품명으로 원재료 코드 조회하기
# 단, 제품명이 HACP 상표 등룍이 완료된 데이터에 한해서만 가능
def getMaterial(context):
    """
        이미지 속 제품명으로 오픈API 호출하여 원재료 정보 추출
        Parameters : context  = 원재료명이 포함된 이미지의 OCR
        - 오픈 API 호출 (단, 제품명이 HACP 상표 등록이 된 경우에 한해서만 조회됨)
        - 호출 API URL : http://apis.data.go.kr/B553748/CertImgListService/getCertImgListService
        Return : prdReportNo = 제품번호
                 prdName = 제품명
                 xmlString =  원재료코드
    """
    # 식품 정보 API
    for x in context.split("\n"):
        if len(x) < 50:
            # STEP1. HACP 원재료 코드 조회
            url = 'http://apis.data.go.kr/B553748/CertImgListService/getCertImgListService'
            params = {'prdlstNm': x.strip(),
                      'serviceKey': 'WUZiEn7bgQjUK7rKJpwF6m+8P0Ni6exh5+07SxdY0E/sM8lF1u/34FkbBzYNRu4zSrztIRW+ng9Lc14+AdFaeg==',
                      'numOfRows': '1', 'returnType': 'xml'}
            response = requests.get(url, params=params)
            rescode = response.status_code

            if (rescode == 200):
                responeBody = response.text
                dom = xml.dom.minidom.parseString((responeBody.encode('utf-8')))

                xmlString = dom.getElementsByTagName("rawmtrl")

                if len(xmlString) != 0:
                    xmlString = xmlString[0].childNodes[0].nodeValue
                    # 제품 - 품목보고번호 prdReportNo
                    prdReportNo = dom.getElementsByTagName("prdlstReportNo")[0].childNodes[0].nodeValue
                    prdName = x.strip()
                    break;

            else:
                print('Error Code', rescode)
                print(response.content)
    return prdReportNo, prdName, xmlString


# step2. 원재료 코드정보 가져오기
def getMaterialInfo(xmlData):
    """
        추출된 원재료명 기준으로 원래료의 상세정보 조회
        Parameters : xmlData  = 원재료명 list
        - 호출 API URL : https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15058665
        Return : rawmtrlAllList = 원재료명(RPRSNT_RAWMTRL_NM), 중분류(MLSFC_NM), 이명(RAWMTRL_NCKNM)
    """
    # 한국어만 추출
    p = re.compile('([ㄱ-힣]+)')
    rawmtrlList = p.findall(xmlData)

    # STEP2. 원재료 코드 정보 가져오기
    # URL : # https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15058665
    rawmtrlAllList = []
    for x in rawmtrlList:
        url = 'http://apis.data.go.kr/1471000/FoodRwmatrInfoService01/getFoodRwmatrList01'
        params = {'rprsnt_rawmtrl_nm': x.strip(),
                  'serviceKey': 'WUZiEn7bgQjUK7rKJpwF6m+8P0Ni6exh5+07SxdY0E/sM8lF1u/34FkbBzYNRu4zSrztIRW+ng9Lc14+AdFaeg==',
                  'pageNo': '1', 'numOfRows': '1', 'type': 'xml'}
        response = requests.get(url, params=params)
        rescode = response.status_code

        if (rescode == 200):

            responeBody = response.text
            dom = xml.dom.minidom.parseString((responeBody.encode('utf-8')))

            xmlString = dom.toxml()
            cnt = dom.getElementsByTagName("totalCount")[0].childNodes[0].nodeValue
            if int(cnt) > 0:
                for x in dom.getElementsByTagName("item"):
                    rawmtrlName = x.getElementsByTagName("RPRSNT_RAWMTRL_NM")[0].childNodes[0].nodeValue
                    mlsfcName = x.getElementsByTagName("MLSFC_NM")[0].childNodes[0].nodeValue
                    rawmtrlNcName = ""
                    if x.getElementsByTagName("RAWMTRL_NCKNM")[0].firstChild != None:
                        rawmtrlNcName = x.getElementsByTagName("RAWMTRL_NCKNM")[0].childNodes[0].nodeValue

                    rwamtralDcit = dict(name=rawmtrlName, mClass=mlsfcName, anoterName=rawmtrlNcName)
                    rawmtrlAllList.append(rwamtralDcit)

        else:
            print('Error Code', rescode)
            print(response.content)

    return rawmtrlAllList


# 비건 유형 및 성분표 분류 함수
def getVeganStep(rawmtrlAllList):
    """
        원재료의 상세정보를 분류 및 비건 유형 추출
        Parameters : rawmtrlAllList = 원재료명(RPRSNT_RAWMTRL_NM), 중분류(MLSFC_NM), 이명(RAWMTRL_NCKNM)파일명
        - 비건 7단계로 구분하여 비건유형 분류 작업 수행
    """
    veganClassList = ["비건", "락토", "오브", "락토오브", "페스코", "폴로", "플렉시"]
    rawmtrlType = dict(vegan=0, milk=0, egg=0, seafood=0, chicken=0, meet=0)
    veganDataList = []
    lactoDataList = []
    ovaDataList = []
    # lactoOvaDatalist = []

    pescoDataList = []
    polloDataList = []
    flexDataList = []

    metrialClassList = []
    for x in rawmtrlAllList:

        if x["mClass"] == '축산물':
            # '계란여부'
            if '계란' in x["name"]:
                rawmtrlType['egg'] = 1
                ovaDataList.append(x["name"])
                # lactoOvaDatalist.append(x["name"])
            # '유제품여부'
            elif '우유' in x["name"] or '치즈' in x["name"] or '분유' in x["name"] or '발효유' in x["name"]:
                rawmtrlType['milk'] = 1
                lactoDataList.append(x["name"])
                # lactoOvaDatalist.append(x["name"])
            # 닭고기 여부
            elif '닭' in x["anoterName"]:
                rawmtrlType['chicken'] = 1
                polloDataList.append(x["name"])
            # 그외 나머지 다 육식
            else:
                rawmtrlType['meet'] = 1
                flexDataList.append(x["name"])

        elif x["mClass"] == '수산물':
            # 수산물 여부 확인
            rawmtrlType['seafood'] = 1
            pescoDataList.append(x["name"])

        elif x["mClass"] == '식물':
            rawmtrlType['vegan'] = 1
            veganDataList.append(x["name"])

    rawmtrNumber = ''.join(list(map(str, rawmtrlType.values())))

    metrialClassList.append(list(set(veganDataList)))
    metrialClassList.append(list(set(lactoDataList)))
    metrialClassList.append(list(set(ovaDataList)))
    metrialClassList.append(list(set(pescoDataList)))
    metrialClassList.append(list(set(polloDataList)))
    metrialClassList.append(list(set(flexDataList)))

    typeList = []

    # idx : 1,2 : 락토, 오브 data
    for idx, chk in enumerate(rawmtrNumber[:: -1]):
        if chk == "1":

            if idx in (3, 4):
                templist = []
                templist.append(veganClassList[len(veganClassList) - 2 - idx])
                templist.extend(veganClassList[3:])
                typeList = templist

            else:
                typeList = veganClassList[len(veganClassList) - 1 - idx:]
            break


    return typeList, metrialClassList




def getContext(tempStr, splitStr="\n"):
    """
        이미지 속 추출된 글자에 대한 전처리 진행
        Parameters : tempStr = text
                     splitStr = 구분자
        - 이미지 속 추출된 글자 중 원재료 정보가 아닌 글자 제외 및 구분자 기준으로 문자 연결
        Return : context = text 전처리 결과
    """
    splitList = tempStr.split(splitStr)
    maxCnt = max([len(x) for x in splitList])
    context = ""
    for line in splitList:
        if len(line) >= (maxCnt / 2):
            context += line
    return context


# 상품 속 이미지의 원재료명 및 제품명 가져오기
def getPrdInfo(ocr_dict):
    """
        이미지 속 원재료명 및 제품명 추출
        Parameters : ocr_dict = 20개 이미지에 대한 OCR 결과
        - 20개 이미지의 원재료명 및 제품명 추출
        Return : prdName = 제품명
                rawmtrlAllList = 원재료정보
    """
    nameList = []
    materialList = []
    rawmtrlAllList = []
    prdName =""

    for key, values in ocr_dict.items():
        if "원재료명" in values:
            materialList.append(key)
        if "제품명" in values:
            nameList.append(key)

    # 제품명으로 원재료코드 가져오기
    for i in nameList:
        context = ocr_dict[i].replace(" ", '\n')
        # "\n" 구분자, HACP API 호출
        prdReportNo, prdName, materString = getMaterial(context)

        if materString != "":
            rawmtrlAllList.extend(getMaterialInfo(materString))
            break

    # 제품명의 원재료정보가 없는 경우  원재료 ocr로  정보 조회
    if rawmtrlAllList == []:
        for i in materialList:
            context = getContext(ocr_dict[i], "\n")
            # 원재료명API 호출
            rawmtrlAllList.extend(getMaterialInfo(context))
    return prdName, rawmtrlAllList


def changeType(lastType, metrialClassList):
    """
    :param lastType: 비건 유형 리스트
    :param metrialClassList:  원재료 구분 리스트
    :return: json type으로 변경
    """
    veganClassList = ["비건", "락토", "오브", "락토오브", "페스코", "폴로", "플렉시"]

    context = {}
    context["type"] = lastType
    context["dataList"] = []
    """
    for x in lastType :
        context["type"].append({veganClassList.index(x): x})
    """

    for i in range(0, len(metrialClassList)):
        if metrialClassList[i] != []:
            idx = "idx" + str(i)
            context["dataList"].append({idx: ','.join(metrialClassList[i])})

    # context["idxCnt"] = len([x for x in metrialClassList if x != []])

    return context