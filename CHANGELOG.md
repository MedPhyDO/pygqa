# Änderungsprotokoll / CHANGELOG

## 0.1.0 / 2021-01-16
- First Release

## 0.1.1 / 2021-04-27
- add isp/client.py - using the same api calls on server
- add isp/dicom.py - enables dicom calls via pynetdicom
- change isp/webapp.py / safrs.py - allows multiple databases with bind parameter
- change isp/mpdf.py - add mode parameter to text() for markdown support

## 0.1.2 / 2021-04-30
- change app/api.py - add/change configs table
- change app/aria.py - modify version
- change app/ariadicom.py - using isp/dicom.py - changes for config settings
- change app/base.py - add evaluationPrepare() and evaluationResult()
- change app/config.py - json_dump parameter
- change app/image.py - remove unused imports
- change app/qa/field.py - changes for config settings - add test 7.2 and 7.3 - change 4.1.2, 7.4 and 7.5
- change app/qa/mlc.py - changes for config settings
- change app/qa/vmat.py - changes for config settings
- change app/qa/wl.py - changes for config settings

## 0.1.3 / 2021-05-19
- change isp/dicom.py - change debug messages
- change isp/safrs.py - changes in additional api results, add _extendedSystemCheck
- change isp/webapp.py - change cors header
- change app/__init__.py - add _extendedSystemCheck
- Some ui changes for _extendedSystemCheck

## 0.1.4 / 2021-06-02
- change app/aria.py - change result from getImageInfos() for missing parameters
- add app/api.py - info() gives infos from database for one year

## 0.1.5 / 2021-08-26
- change app/aria.py - remove get_SubTag_from_MLCPlanType() for missing subTag
- change app/aria.py - add engine for using pytds or pyodbc
