import Box from '@mui/material/Box';
import {useLoaderData, useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, useEffect, useMemo, useRef, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import DocControlPanel from "./DocControl";
import {setTitle} from "../reducers/appBarSlice";
import {loadInNewDocs, loadInOlderDocs, nextIdx, prevIdx, setDoc} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button, Typography} from "@mui/material";
import {DetectedObject} from "../api/models/object";
import {ImageDocument} from "../api/models/imgdoc";
import {Label} from "../api/models/label";


export const BBOX_COLORS = [
    '#E6194B',
    '#4363D8',
    '#FFE119',
    '#3CB44B',
    '#911EB4',
    '#800000',
    '#000075',
    '#F58231',
    '#A9A9A9',
    '#42D4F4',
]

export const getLabel = (labelsMap: [string, Label][] | undefined, obj: DetectedObject) => {
    let label: Label | undefined = undefined;
    if (!!labelsMap) {
        for (let i = 0; i < labelsMap.length; i++) {
            if (labelsMap[i][0] === obj.labelId) {
                label = labelsMap[i][1];
            }
        }
    }
    return label
}

const ProjectIDocPage: FC = () => {
    const {projectName, docId} = useParams();
    const context: any = useOutletContext();
    const idoc: any = useLoaderData();
    const imgContainer = useRef<HTMLDivElement>(null);
    const [imgUrl, setImgUrl] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const isWorking: boolean = useSelector((state: any) => state.iDoc.annoMode);
    const cacheSize: number = useSelector((state: any) => state.iDoc.numPrecached);
    const cacheIdx: number = useSelector((state: any) => state.iDoc.fetchedIdx);
    const cachedDocs: ImageDocument[] | undefined = useSelector((state: any) => state.iDoc.fetchedDocs);
    const histIdx: number = useSelector((state: any) => state.iDoc.historyIdx);
    const historyDocs: ImageDocument[] | undefined = useSelector((state: any) => state.iDoc.historyDocs);
    const doc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const showObjs: boolean = useSelector((state: any) => state.iDoc.showObjects);
    const objsVis: boolean[] | undefined = useSelector((state: any) => state.iDoc.objsVis);
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);

    const loadOld = async (docId: string, numFetch: number) => {
        if (project) {
            if (project.numDocs === 0) {
                return []
            }
            let data: any;
            if (isWorking) {
                // TODO: will always get the same data on repeated calls => maybe work with skip or use
                //  the docId to determine from where to start (could use docId, projectId and userId to
                //  uniquely identify the WorkEntry, then use the updateTS to search only entries with older TS).
                data = await getRequest(`project/${project._id}/fetchHistory/${numFetch.toString()}`);
                if (data) return data.result;
            } else {
                numFetch = -numFetch
                data = await getRequest(`project/${project._id}/idoc/${docId}/simplefetch/${numFetch.toString()}`)
                if (data) {
                    let oldDocs: ImageDocument[] = data.result;
                    return oldDocs.reverse()
                }
            }
        }
        return undefined
    }

    const loadPrevDocs = async () => {
        if (!historyDocs && cacheIdx === 0) {
            let result = await loadOld(doc!._id, cacheSize)
            if (result) {
                dispatch(loadInOlderDocs(result));
            }
        } else {
            let numFetch = Math.floor(cacheSize / 2);
            if (historyDocs && histIdx >= numFetch - 1) {
                let result = await loadOld(historyDocs[historyDocs.length - 1]._id, numFetch)
                if (result) {
                    dispatch(loadInOlderDocs(result));
                }
            } else {
                dispatch(prevIdx());
            }
        }
    }

    const loadNew = async (docId: string, numFetch: number) => {
        // this method assumes that documents in a project should generally be presented in the order
        // from the newest document to the oldest to the user (i.e. descending order by creation date)
        if (project) {
            if (project.numDocs === 0) {
                return []
            }
            let data: any;
            if (isWorking) {
                // TODO: maybe transmit the doc IDs of pre-cached docs to exclude from the pool of candidates
                data = await getRequest(`project/${project._id}/randfetch/${numFetch.toString()}`);
            } else {
                data = await getRequest(`project/${project._id}/idoc/${docId}/simplefetch/${numFetch.toString()}`)
            }
            if (data) {
                let newDocs: ImageDocument[] = data.result;
                return newDocs
            }
        }
        return undefined
    }

    const loadNextDocs = async () => {
        // TODO: handle empty array from Doc fetching (maybe in redux slice?) => means "no newer/older docs"
        if (!cachedDocs && histIdx === 0) {
            let result = await loadNew(doc!._id, cacheSize);
            if (result) {
                dispatch(loadInNewDocs(result));
            }
        } else {
            let numFetch = Math.floor(cacheSize / 2);
            if (cachedDocs && cacheIdx >= numFetch - 1) {
                let result = await loadNew(cachedDocs[cachedDocs.length - 1]._id, numFetch);
                if (result) {
                    dispatch(loadInNewDocs(result));
                }
            } else {
                dispatch(nextIdx());
            }
        }
    }

    const onArrowKeys = async (event: any) => {
        if (event.keyCode == 37) {
            await loadPrevDocs();
        } else if (event.keyCode == 39) {
            await loadNextDocs();
        }
    }

    const generateObjectBBoxs = () => {
        if (!!doc) {
            let objs: DetectedObject[] = doc.objects!;
            if (imgContainer.current && objs && objs.length > 0) {
                let imgHeight = imgContainer.current.offsetHeight
                if (imgHeight > 0) {
                    let ratio = imgHeight / doc.height
                    return objs.filter((_, index) => objsVis && objsVis[index])
                        .map((obj, index) => {
                            let color = BBOX_COLORS[index % 10];
                            let label: Label | undefined = getLabel(labelsMap, obj);
                            return <Box key={obj._id} position='absolute' border='solid 5px' borderColor={color}
                                        sx={{top: ratio * obj.tlx - 5, left: ratio * obj.tly - 5}}
                                        width={ratio * (obj.brx - obj.tlx) + 10}
                                        height={ratio * (obj.bry - obj.tly) + 10}
                                        onClick={() => {
                                            if (project && idoc) {
                                                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${doc._id}/${index}`)
                                            }
                                        }}>
                                <Typography color={color} sx={{fontSize: '20px', ml: '4px'}}>
                                    <b color={color}>{!!label ? label.name : obj.labelId}</b>
                                </Typography>
                            </Box>
                        });
                }
            }
        }
    }

    const bboxs = useMemo(generateObjectBBoxs, [doc, imgUrl, labelsMap, objsVis])

    const loadProject = async () => {
        if (projectName) {
            return await getRequest('project/fromUser', encodeURIComponent(projectName!))
        } else {
            navigate('/notfound404')
        }
    }

    const loadDocImage = async (imgDoc: ImageDocument) => {
        if (imgDoc) {
            return await loadImage('idoc/img', imgDoc._id)
        } else {
            navigate('/notfound404')
        }
    }

    useEffect(() => {
        if (!project) {
            loadProject().then(projectData => projectData && dispatch(setProject(projectData.result)))
        }
    }, [projectName]);

    useEffect(() => {
        if (doc && project) {
            loadDocImage(doc).then(file => {
                if (file) {
                    dispatch(setTitle(doc.name));
                    setImgUrl(file);
                    window.history.replaceState(null, '',
                        `/project/${encodeURIComponent(project.title)}/idoc/${doc._id}`)
                }
            });
            // console.log(doc._id)
            // console.log(cacheIdx, cachedDocs)
            // console.log(histIdx, historyDocs)
        }
    }, [doc, project]);

    useEffect(() => {
        context.setControlPanel(<DocControlPanel/>);
        if (idoc) {
            dispatch(setDoc(idoc))
        }
    }, []);

    // TODO: Images that are very wide will reach too far over the borders with 100% height.
    //   Determine the width/height ratio limit after which the width should be limited =>
    //   height can not be 100% in that case (to keep the aspect ratio in tact)
    return (
        <Box height='100%'>
            <Box height='94%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box ref={imgContainer} height='96%' onKeyDown={onArrowKeys} tabIndex={-1} sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    {imgUrl &&
                        <img alt={doc ? doc.name : "preview image"} src={imgUrl} style={{height: '100%'}}/>}
                    {showObjs && bboxs}
                </Box>
            </Box>
            <Box sx={{display: 'flex', width: '100%'}}>
                <Button sx={{width: '50%'}} variant='outlined' disabled={historyDocs && historyDocs.length === 0}
                        onClick={loadPrevDocs}>Previous</Button>
                <Button sx={{width: '50%'}} variant='outlined' disabled={cachedDocs && cachedDocs.length === 0}
                        onClick={loadNextDocs}>Next</Button>
            </Box>
        </Box>
    )
}

export default ProjectIDocPage
