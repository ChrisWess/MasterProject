import {FC, useEffect, useMemo, useState} from "react";
import Box from "@mui/material/Box";
import {Divider, IconButton, List, ListItem} from "@mui/material";
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
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);

    const annoList = useMemo(() => {
        let objs = idoc?.objects;
        if (objs && objIdx !== undefined) {
            let annos = objs[objIdx].annotations
            return (<List className="annotations" key="annoList">
                {annos?.map((anno, index) =>
                    <ListItem divider key={'annoItem' + index}>
                        <ListItemText key={'annoText' + index}>
                            <Typography variant='h6' color='primary.light'>
                                {anno.text}
                            </Typography>
                        </ListItemText>
                    </ListItem>)}
            </List>)
        }
        return undefined
    }, [idoc])

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
        if (idoc && idoc.objects && objIdx != undefined && labelsMap) {
            let mappedLabel = getMappedLabel(labelsMap, idoc.objects[objIdx].labelId);
            mappedLabel && dispatch(setObjectLabel(mappedLabel));
        }
    }, [idoc, objIdx, labelsMap]);

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
            <Divider/>
            {!!annoList && annoList}
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default ObjectControlPanel
