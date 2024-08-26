import {FC, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Autocomplete, Button, Chip, TextField} from "@mui/material";
import {useDispatch, useSelector} from "react-redux";
import {deleteRequest, getRequest, postRequest, putRequest} from "../api/requests";
import {addLabelMapEntry, addVisibleObj, resetLabelMap, setDoc} from "../reducers/idocSlice";
import Typography from "@mui/material/Typography";
import {Label} from "../api/models/label";
import {DetectedObject} from "../api/models/object";
import {setObject, setObjectLabel} from "../reducers/objectSlice";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {clearBbox} from "../reducers/objectCreateSlice";


export const fetchLabel = async (labelId: string) => {
    return await getRequest('label', labelId)
}


interface LabelSelectProps {
    labelCaption: string;
    categoriesCaption: string;
    categoriesDescriptor: string;
    labelButtonText: string;
    categoryButtonText: string;
    makeNewObject: boolean;  // false := label update
    setAlertContent: Function;
    setAlertSeverity: Function;
    params?: any;
}

const LabelSelect: FC<LabelSelectProps> = ({
                                               labelCaption,
                                               categoriesCaption,
                                               categoriesDescriptor,
                                               labelButtonText,
                                               categoryButtonText,
                                               makeNewObject,
                                               setAlertContent,
                                               setAlertSeverity,
                                               params
                                           }) => {
    const [labelValue, setLabelValue] = useState<string>('');
    const [labelIdx, setLabelIdx] = useState<number>();
    const [queriedLabels, setQueriedLabels] = useState<any[]>([]);
    const [categoryList, setCategoryList] = useState<string[]>([]);
    const [category, setCategory] = useState<string>('');
    const [assignedCategories, setAssignedCategories] = useState<string[]>([]);
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    const userInfo = useSelector((state: any) => state.user.value);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const newBbox: any | undefined = useSelector((state: any) => state.newObj.newBbox);

    const searchLabels = async (event: any, value?: any) => {
        event.preventDefault()
        let queryLabels;
        let stringInput: string;
        if (value) {
            stringInput = value.lower;
        } else {
            stringInput = event.target.value;
        }
        if (stringInput.length > 2) {
            let data = await getRequest('label/search', undefined,
                {query: stringInput.toLowerCase()})
            if (data) {
                let result = data.result
                queryLabels = result.map((value: [string, string]) => {
                    return {id: value[0], label: value[1], lower: value[1].toLowerCase()}
                });
            }
        } else {
            queryLabels = [];
        }
        setLabelValue(stringInput);
        return {result: queryLabels, value: stringInput}
    }

    const fetchLabelCategories = async (queryResult: any) => {
        let labelList: any[] = queryResult.result;
        let valueIdx = labelList.findIndex(value => value.lower === queryResult.value.toLowerCase());
        if (valueIdx >= 0) {
            let match = labelList[valueIdx];
            if (makeNewObject) {
                getRequest('label', match.id, {categories: 1}).then(
                    data => data && setAssignedCategories(data.result.categories))
            }
            setLabelIdx(valueIdx)
        } else if (labelIdx !== undefined && labelIdx >= 0) {
            setLabelIdx(undefined)
            if (makeNewObject) {
                setAssignedCategories([])
            }
        }
        setQueriedLabels(labelList);
    }

    const addCategoriesToLabel = async (label: Label) => {
        return await putRequest('label/categories',
            {labelId: label._id, categories: selectedCategories})
    }

    const handleAddCategoriesToLabel = () => {
        if (objectLabel) {
            addCategoriesToLabel(objectLabel).then(data => {
                if (data) {
                    let newCategories = [...assignedCategories, ...selectedCategories]
                    let newLabel = {...objectLabel, categories: newCategories}
                    dispatch(setObjectLabel(newLabel))
                    setAssignedCategories(newCategories)
                    setSelectedCategories([])
                } else {
                    setAlertSeverity('error')
                    setAlertContent('Error while adding new categories to the label!')
                }
            })
        }
    }

    const handleUpdateLabel = async () => {
        if (detObj && objectLabel) {
            let data = undefined;
            if (labelValue) {
                let objId = detObj._id;
                if (labelIdx !== undefined && labelIdx >= 0) {
                    let newLabelId = queriedLabels[labelIdx].id;
                    if (newLabelId === objectLabel._id) {
                        if (selectedCategories.length > 0) {
                            handleAddCategoriesToLabel()
                            return
                        }
                    } else {
                        data = await putRequest('object/label',
                            {objectId: objId, labelId: newLabelId, categories: selectedCategories})
                    }
                } else {
                    let initialCategories = selectedCategories.length ? selectedCategories : assignedCategories
                    data = await postRequest('object/label/new',
                        {objectId: objId, label: labelValue, categories: initialCategories})
                }
                if (data) {
                    let newLabelId = data.result.updatedTo.set.labelId;
                    if (idoc && idoc.objects && objIdx !== undefined) {
                        let updObj = {...detObj, labelId: newLabelId}
                        let newObjs = [...idoc.objects?.slice(0, objIdx), updObj, ...idoc.objects?.slice(objIdx + 1)]
                        let newDoc = {...idoc, objects: newObjs}
                        dispatch(setObject(updObj))
                        dispatch(setDoc(newDoc))
                    }
                    fetchLabel(newLabelId).then(data => data && dispatch(setObjectLabel(data.result)))
                    setLabelValue('')
                    dispatch(resetLabelMap())
                    setSelectedCategories([])
                }
            } else if (selectedCategories.length > 0) {
                handleAddCategoriesToLabel()
            }
        }
    }

    const handleInsertObject = async () => {
        if (assignedCategories.length + selectedCategories.length > 0) {
            if (labelValue && idoc && newBbox) {
                let data;
                if (labelIdx !== undefined && labelIdx >= 0) {
                    let newLabelId = queriedLabels[labelIdx].id;
                    data = await postRequest('object', {
                        docId: idoc._id, labelId: newLabelId,
                        bboxTlx: newBbox.tlx, bboxTly: newBbox.tly, bboxBrx: newBbox.brx, bboxBry: newBbox.bry
                    })
                } else {
                    data = await postRequest('object', {
                        docId: idoc._id, labelName: labelValue, categories: selectedCategories,
                        bboxTlx: newBbox.tlx, bboxTly: newBbox.tly, bboxBrx: newBbox.brx, bboxBry: newBbox.bry
                    })
                }
                if (data) {
                    let labelId = data.result.labelId;
                    fetchLabel(labelId).then(data => {
                        if (data) {
                            let label = data.result
                            dispatch(setObjectLabel(label))
                            dispatch(addLabelMapEntry([labelId, label]))
                        }
                    })
                    dispatch(addVisibleObj())
                    let now = Date.now().toString()
                    let obj = {
                        ...newBbox, annotations: [], labelId: labelId,
                        createdBy: userInfo._id, createdAt: now, updatedAt: now
                    }
                    dispatch(clearBbox())
                    let newObjs = idoc.objects ? [...idoc.objects, obj] : [obj]
                    let newDoc = {...idoc, objects: newObjs}
                    dispatch(setObject(obj))
                    dispatch(setDoc(newDoc))
                    setLabelValue('')
                    params.resetRect()
                    setAlertSeverity('success')
                    setAlertContent(`New Object was added to image document "${idoc.name}"!`)
                }
            }
        } else {
            setAlertSeverity('error')
            setAlertContent('You need to specify at least one category!')
        }
        // TODO: show errors when failed
    }

    const handleCategorySelection = (event: any, value?: any) => {
        event.preventDefault()
        if (value) {
            setCategory(value);
        } else {
            setCategory(event.target.value);
        }
    }

    const deleteCategory = async (categoryName: string) => {
        if (objectLabel) {
            let foundIdx: number = objectLabel.categories.indexOf(categoryName)
            if (foundIdx == -1) {
                setAlertSeverity('error')
                setAlertContent('The category that you are trying to delete is not linked to the current label!')
            } else {
                deleteRequest('category/' + categoryName, objectLabel._id).then(data => {
                    if (data) {
                        objectLabel.categories.splice(foundIdx, 1);
                        dispatch(setObjectLabel(objectLabel));
                    } else {
                        setAlertSeverity('error')
                        setAlertContent('Error while deleting the category in the database!')
                    }
                })
            }
        }
    }

    const removeCategoryFromLabel = (cIdx: number) => {
        let categories: string[] = [...selectedCategories.slice(0, cIdx),
            ...selectedCategories.slice(cIdx + 1)]
        setSelectedCategories(categories)
    }

    const addSelectedCategory = () => {
        if (selectedCategories.includes(category)) {
            setAlertSeverity('info')
            setAlertContent('Category is already selected!')
        } else {
            setSelectedCategories([...selectedCategories, category])
        }
        setCategory('')
    }

    useEffect(() => {
        if (!makeNewObject && objectLabel) {
            setAssignedCategories(objectLabel.categories)
        }
    }, [objectLabel]);

    useEffect(() => {
        getRequest('category').then(data => data ? setCategoryList(data.result) : navigate(''))
    }, []);

    return (
        <>
            <Typography sx={{mb: 0.5, pt: 1, color: 'text.secondary'}} variant='h6'>{labelCaption}</Typography>
            <Box sx={{display: 'flex', mb: 2}}>
                <Autocomplete
                    freeSolo selectOnFocus handleHomeEndKeys openOnFocus
                    onChange={(e, value) =>
                        searchLabels(e, value).then(result => fetchLabelCategories(result))
                    }
                    options={queriedLabels.sort((a, b) => a.lower.localeCompare(b.lower))} sx={{width: "70%"}}
                    renderInput={(params) =>
                        <TextField {...params} label="Input a label"
                                   onChange={(e) =>
                                       searchLabels(e).then(result => fetchLabelCategories(result))
                                   }
                                   value={labelValue}
                                   sx={{
                                       "& .MuiOutlinedInput-notchedOutline": {
                                           borderColor: "#9090C0",
                                       }
                                   }}/>}
                />
                <Button
                    disabled={makeNewObject ? !newBbox || labelValue.length < 3 || selectedCategories.length + assignedCategories.length == 0 :
                        labelValue.length < 3 && selectedCategories.length == 0}
                    sx={{width: "30%"}} onClick={makeNewObject ? handleInsertObject : handleUpdateLabel}>
                    {labelButtonText}
                </Button>
            </Box>
            <Typography sx={{mb: 0.5, color: 'text.secondary'}} variant='h6'>{categoriesDescriptor}</Typography>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <Typography sx={{pr: 1, my: 'auto'}}>Add Category: </Typography>
                <Autocomplete
                    freeSolo handleHomeEndKeys openOnFocus
                    onChange={(e, value) => handleCategorySelection(e, value)}
                    options={categoryList.sort((a, b) => a.localeCompare(b))} sx={{flexGrow: 80}}
                    renderInput={(params) =>
                        <TextField {...params} label="Select a category"
                                   onChange={(e) => handleCategorySelection(e)}
                                   value={category}
                                   sx={{
                                       "& .MuiOutlinedInput-notchedOutline": {
                                           borderColor: "#9090C0",
                                       }
                                   }}/>}
                />
                <Button disabled={category.length < 2} sx={{width: "30%"}} onClick={addSelectedCategory}>
                    {categoryButtonText}
                </Button>
            </Box>
            <Typography sx={{mb: 0.5, pt: 1}}>{categoriesCaption}</Typography>
            <Box sx={{display: 'flex', mb: 1, border: '1px solid #181818', bgcolor: '#272727', minHeight: 50, p: 1}}>
                {<>
                    {assignedCategories.map((category, index) =>
                        <Chip key={'categ' + index} label={<b>{category}</b>}
                              sx={{
                                  textShadow: '0px 0.5px 0px black', fontSize: '15px', bgcolor: '#672400',
                                  mx: 0.5, my: 0.2
                              }}
                              onDelete={() => deleteCategory(category)}/>)}
                    {selectedCategories.map((category, index) =>
                        <Chip key={'newCateg' + index} label={<b>{category}</b>} color='primary'
                              sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px', mx: 0.5, my: 0.2}}
                              onDelete={() => removeCategoryFromLabel(index)}/>)}
                </>}
            </Box>
        </>
    )
}

export default LabelSelect
