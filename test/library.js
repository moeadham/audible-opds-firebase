import chai from "chai";
import chaiHttp from "chai-http";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";

const ENV = "TEST";

let ENV_PATH = `${process.cwd()}/../functions/.env.local`;

if (ENV != "TEST") {
  ENV_PATH = `${process.cwd()}/../functions/.env.visibl-dev`;
}
dotenv.config({ path: ENV_PATH });
let BUCKET_NAME = process.env.BUCKET_NAME
let APP_URL = process.env.APP_URL;  
let API_KEY = process.env.API_KEY;
chai.use(chaiHttp);
const expect = chai.expect;

describe("test audible", () => {

  it(`get library`, async () => {
    // Read the auth file
    const authFilePath = path.join(process.cwd(), "audible_credentials.json");
    const authData = JSON.parse(fs.readFileSync(authFilePath, "utf8"));
    const response = await chai
      .request(APP_URL)
      .post("/audible_get_library")
      .set("API-KEY", API_KEY)
      .send({
        auth: authData,
      });
    const result = response.body;
    expect(response).to.have.status(200);
    expect(result).to.have.property("status");
    expect(result.status).to.equal("success");
    expect(result).to.have.property("library");
    expect(result.library).to.be.an("array");

    console.log("Library items:");
    result.library.forEach(item => {
      console.log(item);
    });
  });
});
