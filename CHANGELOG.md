# CHANGELOG
## 0.2.1 / 2024-03-19
- change to pylinac 3.20.x
- change app/aria.py 
  - add is_FFF to getImageInfos() result
- change app/qa/field.py 
  - split ```doJT_7_5()``` add ```doJT_7_5_pre2020()``` 
  - remove ```FSImage``` and ```pointRotate``` class
  - refactoring ```doJT_9_1_2()```
  - overrides pylinac ```_plot_field_edges()``` add center line, 80% Area
  - change ```doMT_4_1_2 ()``` reference field without calculation
  - change ```plot4Qprofile()``` swap set_ticks, set_ticklabels to prevent plot warning
  - change ```find4Qdata()``` use FWXMProfilePhysical instead MultiProfile
- change app/qa/mlc.py 
  - remove ```PFImage``` class
  - remove ```_leaves_in_view()```
  - refactoring ```doJT_LeafSpeed()```
  - change ```FWHM_findLeafs()``` use FWXMProfilePhysical instead SingleProfile
  - change ```doJT_10_3_1()``` use FWXMProfilePhysical instead SingleProfile
  - change ```FWHM_plot_errorBox()``` swap set_ticks, set_ticklabels to prevent plot warning
- change app/qa/vmat.py 
  - remove ```FSImage``` class
- change some configuration keys for test parameters
- change ```base.py``` seperate some code from evaluationResult() to evaluationCalculate()
- some code cleanups

## 0.2.0 / 2023-09-05
- changes for python 3.11
  - change isp/mpdf.py 
    - ```mathtext()``` and ```pandas()``` changes
  - change isp/safrs.py 
    - ```_get_connection``` to set/get db_bind in config
    - RQLQuery for compatibility with sqlalchemy >=1.4 since newer rqlalchemy (0.4.5) depends on sqlalchemy <2.0 and >=1.2
    - suppress double call appInfo/appError depends on ```_s_get()``` and ```_s_count()```
  - isp/webapp.py 
    - change ```__init__``` and ```_create_app``` to set/get db_bind in config
    - use javascript openapi-explorer instead python based flask_swagger_ui
    - change building of sphinx documentation
  - app/api.py 
    - ```pandas()``` changes
  - app/ariadicom.py 
    - ```pandas()``` changes
  - app/base.py 
    - use ```pd.concat``` instead ```append()```
    - ```fullCheck.values()``` instead ```fullCheck```
- changes for pylinac 3.14.x
  - app/ispCheckClass.py 
    - use instance of ```DicomImage``` instead ```BaseImage```
    - remove inheritance ```plotClass```
    - remove function ```show()```
  - app/image.py 
    - ```mm2dots_X()```, ```mm2dots_Y()``` 
      - position always greater than or equal to 0 
    - class ```DicomImage```
      - infos default is now dict
      - ```plotImage()```
        - use ```plotClass``` instead function ```initPlot()``` and close plot after use
      - ```cropField()```
        - use ```getFieldDots()``` instead ```mm2dots_X()``` / ```mm2dots_Y()``` for each value
        - now returns DicomImage class instead croped image array 
  - app/qa/field.py 
    - class ```FSImage```
      - use inheritance ```FieldAnalysis``` instead ```FlatSym```
      - ```getProfileData()```
        - change flatness_calculation in ```getProfileData()```
      - ```plotProfile()```
        - use ```plotClass``` instead function ```initPlot()```
        - use new center index calculation
      - ```plot4Qprofile()```
        - use ```plotClass``` instead function ```initPlot()```
  - app/qa/mlc.py 
    - class ```qa_mlc```
      - use new mlc arrangement
      - new property ```abs_mean_error```
      - ```findTransmissions()```
        - use changed ```find_peaks()``` function
      - ```FWHM_findLeafs()```
        - use data from new ```fwxm_data()``` function
      - ```FWHM_plot_error()```
        - use ```plotClass``` instead function ```initPlot()```
      - ```FWHM_plot_errorBox()```
        - use ```plotClass``` instead function ```initPlot()```
        - changes for matplotlib 3.4.0
      - ```plotTransmission()```
        - use ```plotClass``` instead function ```initPlot()```
      - ```picketfence_results()```
        - use new ```results_data()``` function
      - ```picketfence_plotImage()```
        - use ```plotClass``` instead function ```initPlot()```
      - ```_add_leaf_error_subplot()```
        - overrides function and with some modifications
          - use double width on UP_DOWN Chart 
          - draw Leafnumbers 
          - change action_tolerance color to y-
          - set gridlines only on position Axis
    - class ```checkMlc```
      - ```_doMLC_VMAT()```
        - new parameters for analysis
      - ```doJT_10_3_1()```
        - use new fwxm_data for profile
  - app/qa/vmat.py 
    - class ```qa_vmat```
      - use new roi_config for ```analyze()```
      - ```plotChart()```
        - use ```plotClass``` instead function ```initPlot()```
  - app/qa/wl.py 
    - class ```qa_vmat```
      - ```findColliCenter()```
        - use ```getRoi()``` instead ```cropField()```
      - ```_findIsoCalCenter()```
        - use ```getRoi()``` instead ```cropField()```
      - ```findCenterBall()```
        - use ```getRoi()``` instead ```cropField()```
      - ```plotChart()```
        - use ```plotClass``` instead function ```initPlot()```
      - ```plotMergeImage```
        - use ```plotClass``` instead function ```initPlot()```

## 0.1.9 / 2023-05-31
- change app/api.php - ```init()``` better handling for unit names set to null 
- change ui/gqa.phtml - ```GQA_view()``` better handling for unit names set to null 
- change app/base.phtml - ```checkFields()``` better handling of missing Fields
- move spyder to seperate requirements file

## 0.1.8 / 2022-05-30
- remove unused app/dicom.py
- change config files - add units_TestsApp
- change install-resources.py - add copy files to tests
- many changes in isp/ files
- many changes in tests/

## 0.1.7 / 2022-03-28
- many changes in isp/ files
- many changes in tests/

## 0.1.6 / 2021-12-28
- change isp/safrs.py - add count check in _int_json_response
- separate versioning for files in isp/ 
- update requirements.txt and requirements_upgrade.txt
- change app/image.py - plotImage.axTicks() to prevent FixedFormatter warning

## 0.1.5 / 2021-08-26
- change app/aria.py - remove get_SubTag_from_MLCPlanType() for missing subTag
- change app/aria.py - add engine for using pytds or pyodbc

## 0.1.4 / 2021-06-02
- change app/aria.py - change result from getImageInfos() for missing parameters
- add app/api.py - info() gives infos from database for one year

## 0.1.3 / 2021-05-19
- change isp/dicom.py - change debug messages
- change isp/safrs.py - changes in additional api results, add _extendedSystemCheck
- change isp/webapp.py - change cors header
- change ```app/__init__.py``` - add _extendedSystemCheck
- Some ui changes for _extendedSystemCheck

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

## 0.1.1 / 2021-04-27
- add isp/client.py - using the same api calls on server
- add isp/dicom.py - enables dicom calls via pynetdicom
- change isp/webapp.py / safrs.py - allows multiple databases with bind parameter
- change isp/mpdf.py - add mode parameter to text() for markdown support

## 0.1.0 / 2021-01-16
- First Release
