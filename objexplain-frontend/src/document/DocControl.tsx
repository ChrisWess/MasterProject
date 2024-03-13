import {FC, useEffect, useMemo, useState} from "react";
import Box from "@mui/material/Box";
import {
    Button,
    Divider,
    FormControlLabel,
    FormGroup,
    IconButton,
    List,
    ListItem,
    ListItemIcon,
    Switch
} from "@mui/material";
import ButtonTextfield from "../components/ButtonTextfield";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import LabelIcon from '@mui/icons-material/Label';
import AddIcon from '@mui/icons-material/Add';
import {useDispatch, useSelector} from "react-redux";
import {deleteRequest, getRequest, putRequest} from "../api/requests";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {setTitle} from "../reducers/appBarSlice";
import {
    clearDoc,
    disableAnnoMode,
    removeObjectAt,
    setDoc,
    setLabelMap,
    switchObjectsVisible,
    switchObjVisible
} from "../reducers/idocSlice";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';
import {Label} from "../api/models/label";
import {BBOX_COLORS, getLabel} from "./ProjectIDocPage";
import {DetectedObject} from "../api/models/object";


const fetchLabels = async (labelIds: string[]) => {
    if (labelIds.length > 0) {
        let labelPayload = JSON.stringify(labelIds);
        const data = await getRequest('label', undefined,
            {ids: labelPayload, name: 1, categories: 1})
        if (data) {
            return data.result;
        }
    }
    return []
}

export const mapLabels = async (idoc: ImageDocument | undefined) => {
    let objs: DetectedObject[] | undefined = idoc?.objects;
    if (objs) {
        let labelIds = new Set<string>(objs.map(obj => obj.labelId))
        let labels: Label[] = await fetchLabels(Array.from(labelIds.values()));
        let labelMap = new Map<string, Label>()
        for (let i = 0; i < labels.length; i++) {
            let label = labels[i];
            labelMap.set(label._id, label)
        }
        return Array.from(labelMap.entries());
    }
    return undefined
}


const DocControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const objsVis: boolean[] | undefined = useSelector((state: any) => state.iDoc.objsVis);
    const showObjs: boolean = useSelector((state: any) => state.iDoc.showObjects);

    const deleteObject = (objId: string) => {
        if (idoc && idoc.objects) {
            let objIdx = idoc.objects.findIndex(value => value._id === objId);
            if (objIdx >= 0) {
                deleteRequest('object', objId).then(data => {
                    if (data) {
                        dispatch(removeObjectAt(objIdx));
                    } else {
                        setAlertSeverity('error')
                        setAlertContent('Error while deleting the object!')
                    }
                }).catch(error => {
                    // TODO: add such a catch to all other requests
                    setAlertSeverity('error')
                    setAlertContent(error.message)
                })
            } else {
                setAlertSeverity('error')
                setAlertContent('Object with the given ID does not exist in the List of objects!')
            }
        }
    }

    const deleteObjectAtIdx = (objIdx: number) => {
        if (idoc && idoc.objects && objIdx >= 0 && objIdx < idoc.objects.length) {
            deleteRequest('object', idoc.objects[objIdx]._id).then(data => {
                if (data) {
                    dispatch(removeObjectAt(objIdx));
                } else {
                    setAlertSeverity('error')
                    setAlertContent('Error while deleting the object!')
                }
            }).catch(error => {
                setAlertSeverity('error')
                setAlertContent(error.message)
            })
        }
    }

    const renameImage = async (textInput: string) => {
        if (idoc !== undefined) {
            const data = await putRequest('idoc/rename', {docId: idoc._id, docName: textInput})
            if (data) {
                const newIdoc = {...idoc, name: textInput}
                dispatch(setTitle(textInput))
                dispatch(setDoc(newIdoc))
            }
        }
    }

    const toProjectView = () => {
        if (project) {
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const objList = useMemo(() => {
        let objs = idoc?.objects;
        // TODO: error (precondition 3 objs): delete first obj from list => following idxs are removed from list
        if (objs) {
            return (<List className="projects" key="mainList">
                {objs?.map((obj, index) =>
                    <ListItem divider key={'objItem' + index}>
                        <ListItemButton key={'objButt' + index} sx={{py: 0}} onClick={() => {
                            if (project && idoc) {
                                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${index}`)
                            }
                        }}>
                            <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'objIcon' + index}>
                                <LabelIcon sx={{color: BBOX_COLORS[index % 10], mr: 2}}/> {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'objText' + index}>
                                <Typography variant='h6' color='primary.light'>
                                    Label: <b>{!!labelsMap && getLabel(labelsMap, obj)?.name}</b>
                                </Typography>
                            </ListItemText>
                        </ListItemButton>
                        <ListItemIcon>
                            <IconButton onClick={() => dispatch(switchObjVisible(index))}
                                        sx={{color: 'text.secondary'}}>
                                {objsVis && objsVis[index] ?
                                    <VisibilityOffOutlinedIcon/> :
                                    <VisibilityOutlinedIcon/>}
                            </IconButton>
                            <IconButton aria-label="comment" onClick={() => deleteObjectAtIdx(index)}>
                                <DeleteIcon sx={{color: 'text.secondary'}}/>
                            </IconButton>
                        </ListItemIcon>
                    </ListItem>)}
                <ListItem divider key={'newObjItem'}>
                    <ListItemButton key={'newObjButt'} sx={{py: 0}} onClick={() => project && idoc &&
                        navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/newObj`)}>
                        <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'newObjIcon'}>
                            <AddIcon/>
                        </ListItemIcon>
                        <ListItemText key={'newObjText'}>
                            <Typography variant='subtitle1' color='primary.light'>
                                Add new Object
                            </Typography>
                        </ListItemText>
                    </ListItemButton>
                </ListItem>
            </List>)
        }
    }, [idoc, labelsMap, objsVis])

    const onDownloadDocument = () => {
        // TODO: download annotation file and optionally the image (separately)
        // TODO: use the COCO annotation format (file contains doc id and file name to denote which image it refers to):
        //  https://towardsdatascience.com/image-data-labelling-and-annotation-everything-you-need-to-know-86ede6c684b1
        let fileData = JSON.stringify(idoc)
        const blob = new Blob([fileData], {type: "application/json"});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.download = idoc?.fname.split('.')[0] + ".json";
        link.href = url;
        link.click();
    }

    useEffect(() => {
        mapLabels(idoc).then(lm => lm && dispatch(setLabelMap(lm)));
    }, [idoc]);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <IconButton sx={{fontSize: 16, width: 140, mb: 0.5, color: 'secondary.dark'}} onClick={toProjectView}>
                <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Image "{idoc?.name}"</Typography>
            <Typography sx={{color: 'text.secondary'}} variant='caption'>Created At: {idoc?.createdAt}</Typography><br/>
            <Typography sx={{mb: 2, color: 'text.secondary'}} variant='caption'>Last
                Edit: &nbsp;&nbsp; {idoc?.updatedAt}</Typography>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch defaultChecked={showObjs}
                                                   onChange={() => dispatch(switchObjectsVisible())}/>}
                                  label="Show Objects" sx={{mr: 6}}/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 1, pt: 1}}>Rename Image</Typography>
            <ButtonTextfield buttonText='Rename' tfLabel='New name' submitFunc={renameImage} clearOnSubmit
                             style={{paddingBottom: 10}}/>
            <Button sx={{width: '100%', mb: 1}} variant={'outlined'} onClick={onDownloadDocument}>Download File
                Data</Button>
            <Divider sx={{my: 1}}/>
            {!!objList && objList}
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default DocControlPanel
