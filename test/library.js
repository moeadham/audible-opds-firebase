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

  it(`test audible_download_aaxc`, async () => {
    // Read the auth file
    const authFilePath = path.join(process.cwd(), "audible_credentials.json");
    const authData = JSON.parse(fs.readFileSync(authFilePath, "utf8"));
    const response = await chai
      .request(APP_URL)
      .post("/audible_get_library")
      .set("API-KEY", process.env.API_KEY)
      .send({
        auth: authData,
      });
    const result = response.body;
    console.log("response", result);
    expect(response).to.have.status(200);
  });
});
