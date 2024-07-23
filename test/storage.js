import chai from "chai";
import chaiHttp from "chai-http";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";

const ENV = "TEST"

    let ENV_PATH = `${process.cwd()}/../functions/.env.local`
    let CLI_APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/europe-west1";
    let DL_APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/europe-west1";
if (ENV != "TEST"){
    ENV_PATH = `${process.cwd()}/../functions/.env.visibl-dev-ali`
    CLI_APP_URL = "https://audible-cli-test-4f33egefga-ew.a.run.app"
    DL_APP_URL = "https://audible-download-file-4f33egefga-ew.a.run.app"
}

dotenv.config({path: ENV_PATH});

chai.use(chaiHttp);
const expect = chai.expect;




describe("test audible", () => {
    it(`test audible_cli_test`, async () => {
        let countryCode = "ca"
        const response = await chai
            .request(CLI_APP_URL)
            .post("/audible_cli_test")
            .set("API-KEY", process.env.API_KEY)
            .send({ country_code: countryCode });

        expect(response).to.have.status(200);
        const result = response.body;
        console.log("result", result)
        expect(result).to.have.property("message");
        expect(result.message).to.equal("Audible version retrieved successfully");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("success");
    });
    if (ENV == "TEST"){
    it(`test dev_upload_ffmpeg`, async () => {
            const response = await chai
                .request(CLI_APP_URL)
                .post("/dev_upload_ffmpeg")
                .set("API-KEY", process.env.API_KEY)
                .send({});

            expect(response).to.have.status(200);
            const result = response.body;

            expect(result).to.have.property("message");
            expect(result.message).to.equal("FFmpeg binary uploaded successfully");
            expect(result).to.have.property("status");
            expect(result.status).to.equal("success");
            expect(result).to.have.property("destination");
            expect(result.destination).to.be.a('string');
            expect(result.destination).to.equal("gs://visibl-dev-ali/bin/ffmpeg");

            console.log("FFmpeg upload destination:", result.destination);
        });
    }

    it(`test audible_download_file`, async () => {

        // Read the auth file
        const authFilePath = path.join(process.cwd(), 'audible_credentials.json');
        const authData = JSON.parse(fs.readFileSync(authFilePath, 'utf8'));
        const asin = "B08DJC7DQV"
        const response = await chai
            .request(DL_APP_URL)
            .post("/audible_download_file")
            .set("API-KEY", process.env.API_KEY)
            .send({ 
                country_code: "ca",
                auth: authData,
                asin: asin,
                bucket: "visibl-dev-ali",
                path: `UserData/uid/Uploads/AudibleRaw/`
            });
        const result = response.body;
        console.log("response", result)
        expect(response).to.have.status(200);
        expect(result).to.have.property("message");
        expect(result.message).to.equal("Audible file downloaded and uploaded successfully");
        expect(result).to.have.property("status");
        expect(result.status).to.equal("success");
        expect(result).to.have.property("download_output");
        //expect(result.download_output).to.be.a('string');
        expect(result).to.have.property("aax_path");
        expect(result.aax_path).to.be.a('string');
        expect(result.aax_path).to.equal(`UserData/uid/Uploads/AudibleRaw/${asin}.aax`);
        expect(result).to.have.property("m4b_path");
        expect(result.m4b_path).to.be.a('string');
        expect(result.m4b_path).to.equal(`UserData/uid/Uploads/AudibleRaw/${asin}.m4b`);
        console.log("AAX path:", result.aax_path);
        console.log("M4B path:", result.m4b_path);
        console.log("Download output:", result.download_output);
    });
    const DELETE_FILES = false;
    if(DELETE_FILES) {
    it('test delete downloaded files', async () => {
        const downloadsPath = path.join(process.cwd(), '..', 'functions', 'audible-cli', 'downloads');
        
        // Read the directory
        const files = fs.readdirSync(downloadsPath);
        
        // Delete each file
        for (const file of files) {
            fs.unlinkSync(path.join(downloadsPath, file));
        }
        
        // Check if the directory is empty
        const remainingFiles = fs.readdirSync(downloadsPath);
        expect(remainingFiles.length).to.equal(0);
        console.log(`Deleted ${files.length} files from ${downloadsPath}`);
        // Delete files in ../functions/audible-cli
        const audibleCliPath = path.join(process.cwd(), '..', 'functions', 'audible-cli');
        const audibleCliFiles = fs.readdirSync(audibleCliPath);
        
        for (const file of audibleCliFiles) {
            const filePath = path.join(audibleCliPath, file);
            if (fs.lstatSync(filePath).isFile()) {
                fs.unlinkSync(filePath);
            }
        }
        // Check if the directory is empty of files (might still contain subdirectories)
        const remainingAudibleCliFiles = fs.readdirSync(audibleCliPath).filter(file => 
            fs.lstatSync(path.join(audibleCliPath, file)).isFile()
        );
        expect(remainingAudibleCliFiles.length).to.equal(0);
        
        console.log(`Deleted ${audibleCliFiles.length} files from ${audibleCliPath}`);

        
        });
    }
});
    