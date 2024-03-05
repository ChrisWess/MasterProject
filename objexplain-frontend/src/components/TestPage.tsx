import {ChangeEvent, FC, useState} from 'react';
import {Box, Button, Skeleton} from "@mui/material";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import {deleteRequest, getRequest, loadImage, postRequest, putRequest} from "../api/requests";


const TestPage: FC = ({}) => {
    const [thumbnails, setThumbnails] = useState<string[]>();
    const [imageData, setImageData] = useState<any | undefined>();
    // TODO: files and the currently selected imgDocId should be saved in a redux slice
    const [importFile, setImportFile] = useState<any | undefined>();
    const [selectedFile, setSelectedFile] = useState<string | undefined>();
    const [docFile, setDocFile] = useState<string | undefined>();
    const [page, setPage] = useState<number>(1);

    async function deleteImages() {
        await deleteRequest('idoc')
    }

    const loadThumbnails = async (pageIdx: number | undefined) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let page = undefined
        if (pageIdx !== undefined) {
            page = pageIdx.toString()
        }
        let data = await getRequest('idoc/thumbnail', page, {sort_by: 'height'})
        if (data) {
            setThumbnails(data.result)
        }
    }

    const loadDocImage = async (imgId: string) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let data = await loadImage('idoc/img', imgId)
        if (data) {
            setDocFile(data)
        }
    }

    const insertLabel = async () => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let data = await postRequest('label', {
            name: "Patrick Star",
            categories: ["star", "fish"]
        })
        if (data) {
            console.log('Successfully inserted label: ', data.result)
        }
    }

    const insertAnnotatedObject = async (imgId: string) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        // TODO: maybe put payloads like AnnotationPayload in models folder to already
        //  validate field names and types in the frontend
        let data = await postRequest("object/annotated",
            {
                docId: imgId,
                bboxTlx: 0, bboxTly: 0,
                bboxBrx: 100, bboxBry: 100,
                label: 0,
                annotation: "This is a living Starfish, because it is pink and has 5 long, sharp extremities! " +
                    "What happens to this spelling error? Can we use the coisne similarity?"
            }
        );
        if (data) {
            console.log('inserted annotated object: ', data.result)
        }
    }

    const insertMultiAnnotatedObject = async (imgId: string) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let data = await postRequest("object/annotated",
            {
                docId: imgId,
                bboxTlx: 50, bboxTly: 50,
                bboxBrx: 200, bboxBry: 200,
                label: 0,
                annotations: [
                    "This is a live, evil Starfish, because it is pink and has 5 long, sharp extremities!",
                    "The evil starfish have pointy skin and many little suction pads on their back."
                ]
            },
        );
        if (data) {
            console.log('inserted annotated object: ', data.result)
        }
    }

    const insertMultiAnnotatedObject2 = async (imgId: string) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let data = await postRequest("object/annotated",
            {
                docId: imgId,
                bboxTlx: 100, bboxTly: 100,
                bboxBrx: 300, bboxBry: 300,
                label: 0,
                annotations: [
                    "The gray bird has a light grey head and grey webbed feet.",
                    "A large flying bird with and all grey body, long dark wings, webbed feet, and a long sharp bill.",
                    "This bird has wings that are brown and has a long bill",
                ]
            },
        );
        if (data) {
            console.log('inserted annotated object: ', data.result)
        }
    }

    const insertMultiAnnotatedObject3 = async (imgId: string) => {
        // Load image from DB and create a temp image URL in order to be able to display the image.
        let data = await postRequest("object/annotated",
            {
                docId: imgId,
                bboxTlx: 0, bboxTly: 0,
                bboxBrx: 250, bboxBry: 250,
                label: 0,
                annotations: [
                    "This grey bird has an impressive wingspan, a grey bill, and a white stripe that surrounds the feathers near the bill.",
                    "This bird is all black and has a long, pointy beak.",
                ]
            },
        );
        if (data) {
            console.log('inserted annotated object: ', data.result)
        }
    }

    const insertAnnotatedImage = async (event: any) => {
        event.preventDefault();
        // await insertLabel();
        if (!!selectedFile && !!imageData) {
            let exampleObjects: any[] = []
            let annotations: string[] = ["This is an example annotation to test uploads!"]
            exampleObjects.push({
                bboxTlx: 0, bboxTly: 0,
                bboxBrx: 100, bboxBry: 100,
                label: 0, annotations: annotations
            })
            annotations = ["This is another example annotation to test uploads! What happened to blue-feathered Triceratops."]
            exampleObjects.push({
                bboxTlx: 150, bboxTly: 150,
                bboxBrx: 350, bboxBry: 350,
                label: 0, annotations: annotations
            })

            let formData = new FormData();
            formData.append('name', 'TODO: create the necessary form');
            formData.append('objects', JSON.stringify(exampleObjects));
            formData.append('image', imageData);

            // TODO: For very large JSON data sets, especially when dealing with files in the order of
            //  megabytes or more, sending it as a separate file might be more efficient.
            // formData.append('objects', new Blob([JSON.stringify(exampleObjects)], {type: 'application/json'}));

            let data = await postRequest('idoc/annotated', formData,
                'multipart/form-data image/jpeg image/png image/gif image/webp')
            if (data) {
                console.log("response", data)
                let result = data.result
                await loadDocImage(result)
                await loadThumbnails(page)
                window.history.replaceState(null, "", "/idoc/" + result)
                // setPage(page + 1)
            }
        }
    }

    const insertImage = async (event: any) => {
        event.preventDefault();
        if (!!selectedFile && !!imageData) {
            let formData = new FormData();
            formData.append('name', 'Basic Image');
            formData.append('image', imageData);

            let data = await postRequest('idoc', formData,
                'multipart/form-data image/jpeg image/png image/gif image/webp')
            if (data) {
                console.log("response", data)
                let result = data.result
                await loadDocImage(result)
                await loadThumbnails(page)
                window.history.replaceState(null, "", "/idoc/" + result)
            }
        }
    }

    const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        // Request the state and update the state
        let y = (event?.target as HTMLInputElement).files;
        let file;
        if (y != null) {
            file = y[0];
            setImageData(file);
            setSelectedFile(URL.createObjectURL(file));
        }
    };

    const onSubmitFileUpload = async (event: any) => {
        // Uploads the image to the DB and displays it after a successful upload.
        event.preventDefault();
        if (!!selectedFile && !!imageData) {
            let formData = new FormData();
            formData.append('image', imageData);
            formData.append('name', event.target.name.value);
            let data = await postRequest('idoc', formData,
                'multipart/form-data image/jpeg image/png image/gif image/webp')
            if (data) {
                let result = data.result
                await loadDocImage(result)
                await loadThumbnails(page)
                // await insertAnnotatedObject(result)
                await insertMultiAnnotatedObject(result)
                await insertMultiAnnotatedObject2(result)
                await insertMultiAnnotatedObject3(result)
                window.history.replaceState(null, "", "/idoc/" + result)
            }
            setImageData(undefined);
        }
        if (document !== null && document.getElementById('image') !== null) {
            (document.getElementById('image') as HTMLInputElement).value = '';
        }
    };

    const onImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        // Request the state and update the state
        let y = (event?.target as HTMLInputElement).files;
        if (y != null) {
            setImportFile(y[0])
        }
    };

    const onSubmitDataUploadStream = async (event: any) => {
        // Uploads an export file or a dataset file.
        event.preventDefault();
        if (!importFile) {
            alert("Please select a file to upload!");
            return;
        }

        // Just add all the documents to the first best project
        let data = await getRequest('project', undefined, {_id: 1})
        if (data) {
            let projectId = data.result[0]._id
            let formData = new FormData();
            formData.append('file', importFile);
            data = await putRequest('dataset/import', formData, projectId, 'multipart/form-data', {categories: 'bird'})
            if (data) {
                let result = data.result
                console.log(result)
            }
            setImportFile(undefined);
        }
    };

    const onSubmitDataImport = async (event: any) => {
        // Uploads an export file or a dataset file.
        event.preventDefault();
        if (!importFile) {
            alert("Please select a file to upload!");
            return;
        }

        let formData = new FormData();
        formData.append('file', importFile);
        const data = await postRequest('import', formData, 'multipart/form-data')
        if (data) {
            let result = data.result
            console.log(result)
        }
        setImportFile(undefined);
    };

    return (
        <Box sx={{display: 'flex'}}>
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    height: '92.9vh',
                    overflow: 'auto',
                }}
            >
                <Container maxWidth="xl" sx={{mt: 4, mb: 4, marginTop: "100pt"}}>
                    <Grid container spacing={3} rowSpacing={3}
                          sx={{marginLeft: "20%", width: "30%", float: "left"}}>
                        <Grid item xs={12} md={12} lg={12}>
                            <Paper
                                elevation={6}
                                sx={{
                                    p: 2,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    height: 525,
                                    overflow: 'auto'
                                }}>
                                <form onSubmit={onSubmitFileUpload}>
                                    <label htmlFor="image">Select an Image: </label>
                                    <input type="file" id="image" onChange={onFileChange}
                                           accept="image/jpeg,image/png,image/gif,image/webp"/><br/>
                                    <label htmlFor="name">Image Title: </label>
                                    <input type="text" id="name" name="name" required minLength={3} maxLength={60}
                                           size={30}/><br/>
                                    <Button variant="outlined"
                                            style={{margin: 1, textTransform: "none", width: "97%"}}
                                            type="submit" disabled={!selectedFile}> Upload </Button>
                                </form>
                                <form onSubmit={insertAnnotatedImage}>
                                    <label htmlFor="image2">Image with Annotations: </label>
                                    <Button variant="outlined"
                                            style={{margin: 1, textTransform: "none", width: "97%"}}
                                            type="submit" disabled={!selectedFile}> Upload </Button>
                                </form>
                                <form onSubmit={insertImage}>
                                    <label htmlFor="image3">Plain Image: </label>
                                    <Button variant="outlined"
                                            style={{margin: 1, textTransform: "none", width: "97%"}}
                                            type="submit" disabled={!selectedFile}> Upload </Button>
                                </form>
                                <form onSubmit={onSubmitDataImport}>
                                    <input type="file" id="data_import" onChange={onImportFileChange}
                                           accept="ojx"/><br/>
                                    <Button variant="outlined"
                                            style={{margin: 1, textTransform: "none", width: "97%"}}
                                            type="submit" disabled={!importFile}> Import </Button>
                                </form>
                                <Button variant="outlined" style={{margin: 1, textTransform: "none", width: "97%"}}
                                        onClick={deleteImages}> Clear </Button>
                                {!selectedFile ? <>1</> : <img alt="preview image" src={selectedFile}/>}
                                {!docFile ? <>2</> : <img alt="preview image" src={docFile}/>}
                            </Paper>
                        </Grid>
                    </Grid>

                    <Grid container spacing={3} rowSpacing={3}
                          sx={{marginLeft: "10pt", width: "30%", float: "left"}}>
                        <Grid item xs={12} md={12} lg={12}>
                            <Paper
                                elevation={6}
                                sx={{
                                    p: 2,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    height: 525,
                                }}>
                                {thumbnails ?
                                    thumbnails.map((thumb) => <img alt="thumbnail"
                                                                   src={`data:image/png;base64,${thumb}`}
                                                                   width={200}/>) :
                                    <>
                                        <Skeleton variant="rectangular" width={'auto'} height={20}/>
                                        <Skeleton variant="rectangular" style={{marginTop: '10px'}} width={'auto'}
                                                  height={20}/>
                                        <Skeleton variant="rectangular" style={{marginTop: '10px'}} width={'auto'}
                                                  height={20}/>
                                    </>
                                }
                            </Paper>
                        </Grid>
                    </Grid>

                </Container>
            </Box>
        </Box>
    )
}

export default TestPage;
