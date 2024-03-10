import Box from '@mui/material/Box';
import {useLoaderData, useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, useEffect, useMemo, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import DocControlPanel from "./DocControl";
import {setTitle} from "../reducers/appBarSlice";
import {
    initVisibleObjs,
    loadInNewDocs,
    loadInOlderDocs,
    nextIdx,
    prevIdx,
    setDoc,
    setImgUrl
} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button, Typography} from "@mui/material";
import {DetectedObject} from "../api/models/object";
import {ImageDocument} from "../api/models/imgdoc";
import {Label} from "../api/models/label";
import Tooltip from "@mui/material/Tooltip";


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

export const loadProject = async (projectName: string) => {
    return await getRequest('project/fromUser', encodeURIComponent(projectName!))
}

export const loadDocImage = async (docId: string) => {
    return await loadImage('idoc/img', docId)
}

const ProjectIDocPage: FC = () => {
    const {projectName, docId} = useParams();
    const context: any = useOutletContext();
    const idoc: any = useLoaderData();
    const imgContainer = useRef<HTMLDivElement>(null);

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
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
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
                                        sx={{top: ratio * obj.tly - 5, left: ratio * obj.tlx - 5, cursor: 'pointer'}}
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

    const bboxs = useMemo(generateObjectBBoxs, [doc, labelsMap, objsVis])

    useEffect(() => {
        if (!projectName) {
            navigate('/notfound404')
        } else {
            if (!project || project.title != projectName) {
                loadProject(projectName).then(projectData => projectData ?
                    dispatch(setProject(projectData.result)) :
                    navigate('/notfound404'))
            }
        }
    }, [projectName]);

    useEffect(() => {
        if (doc && project && !imgUrl) {
            loadDocImage(doc._id).then(file => {
                if (file) {
                    dispatch(setTitle(doc.name));
                    doc.objects && dispatch(initVisibleObjs(doc.objects.length));
                    dispatch(setImgUrl(file));
                    window.history.replaceState(null, '',
                        `/project/${encodeURIComponent(project.title)}/idoc/${doc._id}`)
                } else {
                    navigate('/notfound404')
                }
            });
        }
    }, [doc, project, imgUrl]);

    useEffect(() => {
        context.setControlPanel(<DocControlPanel/>);
        if (idoc) {
            dispatch(setDoc(idoc))
        } else {
            navigate('/notfound404')
        }
    }, []);

    return (
        <Box height='100%'>
            <Box height='94%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box height='96%' onKeyDown={onArrowKeys} tabIndex={-1} sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    <Box ref={imgContainer} sx={{
                        height: '100%',
                        transform: `scale(${doc ? Math.min(1, (1170 / 716) / (doc.width / doc.height)) : 1})`
                    }}>
                        {doc && imgUrl &&
                            <Tooltip title={`Width: ${doc.width} ; Height: ${doc.height}`}>
                                <img alt={doc.name} src={imgUrl} style={{height: '100%'}}/>
                            </Tooltip>}
                        {showObjs && bboxs}
                    </Box>
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
