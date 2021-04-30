# 0.1.0 / 2021-01-16
- First Release

# 0.1.1 / 2021-04-27
- add isp/client.py - using the same api calls on server
- add isp/dicom.py - enables dicom calls via pynetdicom 
- change isp/webapp.py / safrs.py - allows multiple databases with bind parameter
- change isp/mpdf.py - add mode parameter to text() for markdown support

# 0.1.2 / 2021-04-30
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
