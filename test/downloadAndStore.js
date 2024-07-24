import chai from "chai";
import chaiHttp from "chai-http";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";

const ENV = "TEST";

let ENV_PATH = `${process.cwd()}/../functions/.env.local`;


if (ENV != "TEST") {
  ENV_PATH = `${process.cwd()}/../functions/.env.visibl-dev`;
  dotenv.config({ path: ENV_PATH });
  APP_URL = process.env.APP_URL;
} else {
  dotenv.config({ path: ENV_PATH });
}
let BUCKET_NAME = process.env.BUCKET_NAME
let APP_URL = process.env.APP_URL
let API_KEY = process.env.API_KEY
let TEST_ASIN = "B072LK1GSN"//"B0711P9C1V"//"B08DJC7DQV"

chai.use(chaiHttp);
const expect = chai.expect;

describe("test audible", () => {
  if (ENV == "TEST") {
    it(`test dev_upload_ffmpeg`, async () => {
      const response = await chai
        .request(APP_URL)
        .post("/dev_upload_ffmpeg")
        .set("API-KEY", API_KEY)
        .send({
          bucket: BUCKET_NAME,
        });

      expect(response).to.have.status(200);
      const result = response.body;

      expect(result).to.have.property("message");
      expect(result.message).to.equal("FFmpeg binary uploaded successfully");
      expect(result).to.have.property("status");
      expect(result.status).to.equal("success");
      expect(result).to.have.property("destination");
      expect(result.destination).to.be.a("string");

      console.log("FFmpeg upload destination:", result.destination);
    });
  }

  it(`test audible_download_aaxc`, async () => {
    // Read the auth file
    const authFilePath = path.join(process.cwd(), "audible_credentials.json");
    const authData = JSON.parse(fs.readFileSync(authFilePath, "utf8"));

    const response = await chai
      .request(APP_URL)
      .post("/audible_download_aaxc")
      .set("API-KEY", API_KEY)
      .send({
        country_code: "ca",
        auth: authData,
        asin: TEST_ASIN,
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
    expect(result.aaxc_path).to.include(`${TEST_ASIN}.aaxc`);
    expect(result).to.have.property("metadata");
    expect(result.metadata).to.be.an('object');
    expect(result.metadata).to.have.property('title');
    expect(result.metadata).to.have.property('author').that.is.an('array');
    expect(result.metadata).to.have.property('year');
    expect(result.metadata).to.have.property('bitrate_kbs').that.is.a('number');
    expect(result.metadata).to.have.property('codec');
    expect(result.metadata).to.have.property('chapters').that.is.an('object');
    expect(result.metadata).to.have.property('length').that.is.a('number');

    // Check structure of a chapter
    const firstChapterKey = Object.keys(result.metadata.chapters)[0];
    const firstChapter = result.metadata.chapters[firstChapterKey];
    expect(firstChapter).to.have.property('startTime').that.is.a('number');
    expect(firstChapter).to.have.property('endTime').that.is.a('number');
    // Note: 'title' is optional for chapters, so we don't check for it

    //console.log("Metadata:", JSON.stringify(result.metadata, null, 2));
    console.log("AAXC path:", result.aaxc_path);
    console.log("Download status:", result.download_status);
  });
  const DELETE_FILES = false;
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
