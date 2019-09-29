all:
	go get gopkg.in/yaml.v2
	go get "github.com/dgrijalva/jwt-go"
	go get "github.com/fullsailor/pkcs7"
	go get "github.com/gin-gonic/gin"
	go get "golang.org/x/crypto/ocsp"
	cd cmd/estserver && go build -o ../../build/estserver --ldflags="-w -s"

clean:
	rm build/estserver
