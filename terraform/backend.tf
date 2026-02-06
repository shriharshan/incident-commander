terraform {
  backend "s3" {
    bucket  = "incident-commander-tf-state-279150584211"
    key     = "incident-commander/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
