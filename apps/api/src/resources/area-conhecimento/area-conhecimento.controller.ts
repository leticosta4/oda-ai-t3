import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  ParseUUIDPipe,
  Query,
} from '@nestjs/common';
import { AreaConhecimentoService } from './area-conhecimento.service';
import { CreateAreaConhecimentoDto } from './dto/create-area-conhecimento.dto';
import { UpdateAreaConhecimentoDto } from './dto/update-area-conhecimento.dto';
import { FindAllAreaConhecimentoDto } from './dto/find-all-area-conhecimento.dto';

@Controller('area-conhecimento')
export class AreaConhecimentoController {
  constructor(private readonly areaConhecimentoService: AreaConhecimentoService) {}

  @Post()
  create(@Body() createAreaConhecimentoDto: CreateAreaConhecimentoDto) {
    return this.areaConhecimentoService.create(createAreaConhecimentoDto);
  }

  @Get()
  findAll(@Query() query: FindAllAreaConhecimentoDto) {
    return this.areaConhecimentoService.findAll(query);
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.areaConhecimentoService.findById(id);
  }

  @Patch(':id')
  update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updateAreaConhecimentoDto: UpdateAreaConhecimentoDto,
  ) {
    return this.areaConhecimentoService.update(id, updateAreaConhecimentoDto);
  }
}
