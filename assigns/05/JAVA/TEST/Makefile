JAVAC ?= javac
JAVA ?= java
BUILD_DIR := .build

.PHONY: test test-direct test-vp compile

test: test-direct test-vp

compile:
	mkdir -p $(BUILD_DIR)
	$(JAVAC) --release 17 -Xlint:all -d $(BUILD_DIR) ../Lambda1.java ../Lambda1_vp.java TestLambda1.java TestLambda1_vp.java

test-direct: compile
	$(JAVA) -cp $(BUILD_DIR) TestLambda1

test-vp: compile
	$(JAVA) -cp $(BUILD_DIR) TestLambda1_vp
