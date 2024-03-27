import {FC, useEffect, useMemo, useState} from "react";
import Box from "@mui/material/Box";
import {Button, Divider, IconButton, List, ListItem, ListItemIcon} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {Label} from "../api/models/label";
import ListItemText from "@mui/material/ListItemText";
import LabelSelect from "./LabelSelector";
import {clearObject, setObjectLabel} from "../reducers/objectSlice";
import {clearDoc, disableAnnoMode} from "../reducers/idocSlice";
import ListItemButton from "@mui/material/ListItemButton";
import AddIcon from "@mui/icons-material/Add";
import {DetectedObject} from "../api/models/object";


export const getMappedLabel = (labelsMap: [string, Label][], labelId: string) => {
    for (let i = 0; i < labelsMap.length; i++) {
        if (labelsMap[i][0] === labelId) {
            return labelsMap[i][1]
        }
    }
    return undefined
}


const ObjectControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);

    const annoList = useMemo(() => {
        if (detObj?.annotations && objIdx !== undefined) {
            let annos = detObj.annotations
            return (<List className="annotations" key="annoList">
                <ListItemButton key={'newAnnoButt'} sx={{py: 0}}
                                onClick={() => project && idoc && objIdx !== undefined &&
                                    navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/newAnno`)}>
                    <ListItem divider sx={{height: '60px'}} key={'newAnnoItem'}>
                        <ListItemIcon sx={{color: 'text.secondary'}} key={'newAnnoIcon'}>
                            <AddIcon/>
                        </ListItemIcon>
                        <ListItemText key={'newAnnoText'}>
                            <Typography variant='inherit' color='primary.light'>
                                <b>Add new Annotation</b>
                            </Typography>
                        </ListItemText>
                    </ListItem>
                </ListItemButton>
                {annos?.map((anno, index) =>
                    <ListItemButton key={'annoButt' + index} sx={{py: 0}}
                                    onClick={() => {
                                        if (project && idoc) {
                                            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/${index}`)
                                        }
                                    }}>
                        <ListItem divider key={'annoItem' + index}>
                            <ListItemIcon sx={{color: 'text.secondary', width: '10px'}} key={'annoIcon' + index}>
                                {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'annoText' + index}>
                                <Typography variant='inherit' color='primary.light'>
                                    {anno.text}
                                </Typography>
                            </ListItemText>
                        </ListItem>
                    </ListItemButton>)}
            </List>)
        }
        return undefined
    }, [idoc, detObj, objIdx])

    const toProjectView = () => {
        if (project) {
            dispatch(clearObject())
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toImageView = () => {
        if (project && idoc) {
            dispatch(clearObject())
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}`)
        }
    }

    useEffect(() => {
        if (detObj && labelsMap) {
            let mappedLabel = getMappedLabel(labelsMap, detObj.labelId);
            mappedLabel && dispatch(setObjectLabel(mappedLabel));
        }
    }, [detObj, labelsMap]);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toImageView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Object Label
                "{objectLabel?.name}"</Typography>
            <Divider sx={{my: 1}}/>
            <LabelSelect labelCaption="Update Object Label" labelButtonText='Update'
                         categoriesCaption='Categories of the Label' categoryButtonText='Insert'
                         categoriesDescriptor='Add further Categories: ' makeNewObject={false}
                         setAlertContent={setAlertContent} setAlertSeverity={setAlertSeverity}/>
            <Divider sx={{mb: 1}}/>
            <Button variant='contained' sx={{textTransform: 'none', width: "100%"}} onClick={() => {
                if (project && idoc && objIdx !== undefined) {
                    navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/updObj`)
                }
            }}>
                Update Object Bounding Box
            </Button>
            <Divider sx={{mt: 1}}/>
            <Box sx={{maxHeight: '40%', overflow: 'auto'}}>
                {!!annoList && annoList}
            </Box>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default ObjectControlPanel
