import chai from "chai";
import chaiHttp from "chai-http";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";

const ENV = "TEST";

let ENV_PATH = `${process.cwd()}/../functions/.env.local`;
let APP_URL = "http://127.0.0.1:5001/visibl-dev-ali/europe-west1";

if (ENV != "TEST") {
  ENV_PATH = `${process.cwd()}/../functions/.env.visibl-dev-ali`;
  dotenv.config({ path: ENV_PATH });
  APP_URL = process.env.APP_URL;
} else {
  dotenv.config({ path: ENV_PATH });
}
let BUCKET_NAME = process.env.BUCKET_NAME

chai.use(chaiHttp);
const expect = chai.expect;

describe("test audible", () => {
  if (ENV == "TEST") {
    it(`test dev_upload_ffmpeg`, async () => {
      const response = await chai
        .request(APP_URL)
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
      expect(result.destination).to.be.a("string");
      expect(result.destination).to.equal("gs://visibl-dev-ali/bin/ffmpeg");

      console.log("FFmpeg upload destination:", result.destination);
    });
  }

  it(`test audible_download_aaxc`, async () => {
    // Read the auth file
    const authFilePath = path.join(process.cwd(), "audible_credentials.json");
    const authData = JSON.parse(fs.readFileSync(authFilePath, "utf8"));
    const asin = "B08DJC7DQV";
    const response = await chai
      .request(APP_URL)
      .post("/audible_download_aaxc")
      .set("API-KEY", process.env.API_KEY)
      .send({
        country_code: "ca",
        auth: authData,
        asin: asin,
        bucket: BUCKET_NAME,
        path: `UserData/uid/Uploads/AudibleRaw/`,
      });
    const result = response.body;
    console.log("response", result);
    expect(response).to.have.status(200);
    expect(result).to.have.property("message");
    expect(result.message).to.equal(
      "Audible file downloaded and uploaded successfully"
    );
    expect(result).to.have.property("status");
    expect(result.status).to.equal("success");
    expect(result).to.have.property("download_status");
    expect(result.download_status).to.be.a("string");
    expect(result).to.have.property("aaxc_path");
    expect(result.aaxc_path).to.be.a("string");
    expect(result.aaxc_path).to.include(`${asin}.aaxc`);
    console.log("AAXC path:", result.aaxc_path);
    console.log("Download status:", result.download_status);
  });
  const DELETE_FILES = true;
  if (DELETE_FILES) {
    it("test delete downloaded files", async () => {
      const downloadsPath = path.join(
        process.cwd(),
        "..",
        "functions",
        "bin",
        "downloads"
      );

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
    });
  }
});
